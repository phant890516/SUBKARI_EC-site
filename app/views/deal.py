# ==========================================================
# Filename      : app/views/deal.py
# Descriptions  : Transaction management pages
# ==========================================================
from flask import (Blueprint, render_template, request, make_response,
                   redirect, url_for, current_app, session, jsonify)
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import mysql.connector
import json
import os

deal_bp = Blueprint('deal', __name__, url_prefix='/deal')

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}


# ---------------------------------------------------------------------------
# DB connection
# ---------------------------------------------------------------------------
def connect_db():
    con = mysql.connector.connect(
        host=os.environ.get('AIVEN_DB_HOST'),
        user=os.environ.get('AIVEN_DB_USER'),
        passwd=os.environ.get('AIVEN_DB_PASSWORD'),
        db='db_subkari',
        port=os.environ.get('AIVEN_DB_PORT'),
        ssl_ca='ca.pem',
        ssl_disabled=False,
    )
    return con


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# Helper: seller info
# ---------------------------------------------------------------------------
def get_seller_info(seller_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    sql = """
        SELECT
            a.firstName,
            a.profileImage,
            a.status,
            a.smoker,
            COUNT(e.id)        AS evaluation_count,
            ROUND(AVG(e.score), 1) AS average_score
        FROM m_account a
        LEFT JOIN t_evaluation e ON a.id = e.recipient_id
        WHERE a.id = %s
        GROUP BY a.id
    """
    cur.execute(sql, (seller_id,))
    result = cur.fetchone()
    cur.close()
    con.close()
    return result


# ---------------------------------------------------------------------------
# Transaction TOP page
# ---------------------------------------------------------------------------
@deal_bp.route('/deal', methods=['GET'])
def deal():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)

    # Products bought by this user
    sql_bought = """
        SELECT
            p.*,
            m.img,
            t.id,
            t.status,
            t.situation,
            t.date
        FROM m_product AS p
        LEFT JOIN m_productimg  AS m ON p.id = m.product_id
        LEFT JOIN t_transaction AS t ON p.id = t.product_id
        WHERE t.customer_id = %s
        ORDER BY p.id ASC
    """
    cur.execute(sql_bought, (user_id,))
    bought_products = cur.fetchall()

    # Products sold by this user
    sql_sell = """
        SELECT
            p.*,
            m.img,
            t.id,
            t.status,
            t.situation,
            t.date
        FROM m_product AS p
        LEFT JOIN m_productimg  AS m ON p.id = m.product_id
        LEFT JOIN t_transaction AS t ON p.id = t.product_id
        WHERE
            p.account_id = %s
        AND p.draft = 0
        AND t.status IS NOT NULL
        GROUP BY p.id
    """
    cur.execute(sql_sell, (user_id,))
    products = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'deal/deal_index.html',
        bought_products=bought_products,
        products=products,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Transaction detail (buyer side)
# ---------------------------------------------------------------------------
@deal_bp.route('/deal/<int:transaction_id>', methods=['GET', 'POST'])
def deal_list(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)

    sql = """
        SELECT
            t.*,
            p.rentalPrice,
            p.purchasePrice,
            m.img
        FROM t_transaction AS t
        LEFT JOIN m_product    AS p ON t.product_id = p.id
        LEFT JOIN m_productimg AS m ON t.product_id = m.product_id
        WHERE t.id = %s
        LIMIT 1
    """
    cur.execute(sql, (transaction_id,))
    transaction = cur.fetchone()

    if not transaction:
        cur.close()
        con.close()
        return redirect(url_for('deal.deal'))

    # Build full image paths
    for photo_field in ('shippingPhoto', 'cleaningPhoto', 'receivedPhoto'):
        if transaction.get(photo_field):
            transaction[photo_field] = f"/static/img/{transaction[photo_field]}"

    session['transaction'] = transaction

    # Comments
    product_id = transaction['product_id']
    cur.execute(
        "SELECT content, createdDate, account_id FROM t_comments "
        "WHERE product_id = %s ORDER BY createdDate DESC",
        (product_id,),
    )
    comments = cur.fetchall()
    cur.close()
    con.close()

    # Calculate charges
    if transaction.get('situation') == '購入':
        price = int(transaction.get('purchasePrice') or 0)
        transaction['charge']  = price * 0.1
        transaction['benefit'] = price - transaction['charge']
    elif transaction.get('situation') == 'レンタル':
        price = int(transaction.get('rentalPrice') or 0)
        transaction['charge']  = price * 0.1
        transaction['benefit'] = price - transaction['charge']

    return render_template(
        'deal/deal_detail.html',
        transaction=transaction,
        comments=comments,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Transaction detail (seller side)
# ---------------------------------------------------------------------------
@deal_bp.route('/deal_seller/<int:transaction_id>', methods=['GET', 'POST'])
def deal_list_seller(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)

    sql = """
        SELECT
            t.*,
            p.rentalPrice,
            p.purchasePrice,
            m.img
        FROM t_transaction AS t
        LEFT JOIN m_product    AS p ON t.product_id = p.id
        LEFT JOIN m_productimg AS m ON t.product_id = m.product_id
        WHERE t.id = %s
        LIMIT 1
    """
    cur.execute(sql, (transaction_id,))
    transaction = cur.fetchone()

    if not transaction:
        cur.close()
        con.close()
        return redirect(url_for('deal.deal'))

    for photo_field in ('shippingPhoto', 'cleaningPhoto', 'receivedPhoto'):
        if transaction.get(photo_field):
            transaction[photo_field] = f"/static/img/{transaction[photo_field]}"

    session['transaction'] = transaction

    product_id = transaction['product_id']
    cur.execute(
        "SELECT content, createdDate, account_id FROM t_comments "
        "WHERE product_id = %s ORDER BY createdDate DESC",
        (product_id,),
    )
    comments = cur.fetchall()
    cur.close()
    con.close()

    if transaction.get('situation') == '購入':
        price = int(transaction.get('purchasePrice') or 0)
        transaction['charge']  = price * 0.1
        transaction['benefit'] = price - transaction['charge']
    elif transaction.get('situation') == 'レンタル':
        price = int(transaction.get('rentalPrice') or 0)
        transaction['charge']  = price * 0.1
        transaction['benefit'] = price - transaction['charge']

    return render_template(
        'deal/deal_seller_detail.html',
        transaction=transaction,
        comments=comments,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Seller info endpoint (AJAX)
# ---------------------------------------------------------------------------
@deal_bp.route('/seller_data/get/<int:customer_id>', methods=['GET'])
def get_seller_data(customer_id):
    try:
        seller_data = get_seller_info(customer_id)
        return jsonify({'success': True, 'data': seller_data})
    except Exception as e:
        print(f'Error: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500


# ---------------------------------------------------------------------------
# Helper: save image to disk
# ---------------------------------------------------------------------------
def _save_upload(file):
    """Save an uploaded image and return (filename, image_url)."""
    filename = secure_filename(file.filename)
    savedata  = datetime.now().strftime('%Y%m%d%H%M%S_')
    filename  = savedata + filename

    save_path = os.path.join(current_app.root_path, 'static', 'img', filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    image = Image.open(file)
    image.save(save_path, quality=90)

    image_url = '/static/img/' + filename
    return filename, image_url


# ---------------------------------------------------------------------------
# Cleaning image upload
# ---------------------------------------------------------------------------
@deal_bp.route('/deal/list/imageUpload/<int:transaction_id>', methods=['GET', 'POST'])
def deal_list_imageUpload(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id     = session.get('user_id')
    transaction = session.get('transaction')

    if request.method == 'GET':
        return render_template('deal/deal_detail.html', upload_success=False, user_id=user_id)

    if 'img' not in request.files or not request.files['img'].filename:
        return render_template(
            'deal/deal_detail.html',
            upload_success=False,
            error='ファイルが選択されていません',
            user_id=user_id,
        )

    file = request.files['img']
    if not _allowed_file(file.filename):
        return render_template(
            'deal/deal_detail.html',
            upload_success=False,
            error='許可されていないファイル形式です',
            user_id=user_id,
            transaction=transaction,
        )

    try:
        filename, image_url = _save_upload(file)

        con = connect_db()
        cur = con.cursor()
        cur.execute(
            "UPDATE t_transaction SET cleaningPhoto = %s, status = %s WHERE id = %s",
            (filename, '返送待ち', transaction_id),
        )
        con.commit()
        cur.close()
        con.close()

        return render_template(
            'deal/deal_detail.html',
            upload_success=True,
            image_url=image_url,
            user_id=user_id,
            transaction=transaction,
        )
    except Exception as e:
        return render_template(
            'deal/deal_detail.html',
            upload_success=False,
            error=f'ファイルの保存に失敗しました: {str(e)}',
            user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Shipping image upload
# ---------------------------------------------------------------------------
@deal_bp.route('/list/shipping/imageUpload/<int:transaction_id>', methods=['POST'])
def deal_list_shipping_imageUpload(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    if 'img' not in request.files or not request.files['img'].filename:
        return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400

    file = request.files['img']
    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': '許可されていないファイル形式です'}), 400

    try:
        filename, image_url = _save_upload(file)

        con = connect_db()
        cur = con.cursor()
        cur.execute(
            "UPDATE t_transaction SET shippingPhoto = %s, status = %s WHERE id = %s",
            (filename, '配達中', transaction_id),
        )
        con.commit()
        cur.close()
        con.close()

        return jsonify({
            'success':   True,
            'message':   'アップロード成功',
            'image_url': image_url,
            'filename':  filename,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'ファイルの保存に失敗しました: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Received image upload (buyer confirms receipt)
# ---------------------------------------------------------------------------
@deal_bp.route('/list/received/imageUpload/<int:transaction_id>', methods=['POST'])
def deal_list_received_imageUpload(transaction_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'ログインが必要です'}), 401

    user_id = session.get('user_id')

    if 'img' not in request.files or not request.files['img'].filename:
        return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400

    file = request.files['img']
    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': '許可されていないファイル形式です'}), 400

    try:
        filename, image_url = _save_upload(file)

        con = connect_db()
        cur = con.cursor(dictionary=True)

        # Determine next status based on situation (rental vs purchase)
        cur.execute("SELECT situation FROM t_transaction WHERE id = %s", (transaction_id,))
        row = cur.fetchone()
        next_status = '取引完了' if (row and row.get('situation') == '購入') else 'レンタル中'

        cur.execute(
            "UPDATE t_transaction SET receivedPhoto = %s, status = %s WHERE id = %s",
            (filename, next_status, transaction_id),
        )
        con.commit()
        cur.close()
        con.close()

        return jsonify({
            'success':   True,
            'message':   'アップロード成功',
            'image_url': image_url,
            'filename':  filename,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'ファイルの保存に失敗しました: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Return shipping image upload (renter sends item back)
# ---------------------------------------------------------------------------
@deal_bp.route('/list/return/imageUpload/<int:transaction_id>', methods=['POST'])
def deal_list_return_imageUpload(transaction_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    if 'img' not in request.files or not request.files['img'].filename:
        return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400

    file = request.files['img']
    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': '許可されていないファイル形式です'}), 400

    try:
        filename, image_url = _save_upload(file)

        con = connect_db()
        cur = con.cursor()
        cur.execute(
            "UPDATE t_transaction SET shippingPhoto = %s, status = %s WHERE id = %s",
            (filename, '返送中', transaction_id),
        )
        con.commit()
        cur.close()
        con.close()

        return jsonify({
            'success':   True,
            'message':   'アップロード成功',
            'image_url': image_url,
            'filename':  filename,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'ファイルの保存に失敗しました: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Return received image upload (seller confirms return)
# ---------------------------------------------------------------------------
@deal_bp.route('/list/returnReceived/imageUpload/<int:transaction_id>', methods=['POST'])
def deal_list_returnReceived_imageUpload(transaction_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'ログインが必要です'}), 401

    user_id = session.get('user_id')

    if 'img' not in request.files or not request.files['img'].filename:
        return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400

    file = request.files['img']
    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': '許可されていないファイル形式です'}), 400

    try:
        filename, image_url = _save_upload(file)

        con = connect_db()
        cur = con.cursor()
        cur.execute(
            "UPDATE t_transaction SET receivedPhoto = %s, status = %s WHERE id = %s",
            (filename, '取引完了', transaction_id),
        )
        con.commit()
        cur.close()
        con.close()

        return jsonify({
            'success':   True,
            'message':   'アップロード成功',
            'image_url': image_url,
            'filename':  filename,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'ファイルの保存に失敗しました: {str(e)}'}), 500
