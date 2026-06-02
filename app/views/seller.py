# ==========================================================
# Filename      : app/views/seller.py
# Descriptions  : Seller-side pages and product management
# ==========================================================
from flask import (Blueprint, render_template, request, make_response,
                   redirect, url_for, jsonify, current_app, session)
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime
import mysql.connector
import json
import os
import base64
import io

seller_bp = Blueprint('seller', __name__, url_prefix='/seller')
# 処理方法: まず選択またはアップロードされたデータをsessionに保存し、
#           最後にformatですべてのデータを一気にDBに登録する。


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


# ---------------------------------------------------------------------------
# Seller TOP page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller', methods=['GET'])
def seller():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    return make_response(render_template('seller/seller_index.html', user_id=user_id))


# ---------------------------------------------------------------------------
# Seller format (new listing) page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/format', methods=['GET'])
def seller_format():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    # DB接続
    con = connect_db()
    cur = con.cursor(dictionary=True)

    sql = """
        SELECT
            address.*
        FROM
            m_account AS account
        LEFT JOIN
            m_address AS address
        ON
            account.id = address.account_id
        WHERE
            account.id = %s
    """
    cur.execute(sql, (user_id,))
    address = cur.fetchall()
    cur.close()
    con.close()

    return render_template('seller/seller_format.html', user_id=user_id)


# ---------------------------------------------------------------------------
# Upload image page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/uploadImg', methods=['GET'])
def seller_uploadImg():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    return render_template('seller/seller_uploadImg.html', user_id=user_id)


# ---------------------------------------------------------------------------
# Single image upload (AJAX)
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/upload', methods=['POST'])
def seller_upload():
    file = request.files.get('file')
    if not file:
        return render_template('seller/seller_format.html')

    filename = secure_filename(file.filename)
    savedata = datetime.now().strftime('%Y%m%d%H%M%S_')
    filename = savedata + filename

    save_dir = os.path.join(current_app.root_path, 'static', 'img')
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    try:
        image = Image.open(file)
        image.save(save_path, quality=90)
        image_url = '/static/img/' + filename
        return jsonify({'success': True, 'image_url': image_url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Products list page
# ---------------------------------------------------------------------------
@seller_bp.route('/products', methods=['GET'])
def seller_products():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)

    # All published products
    sql = """
        SELECT
            p.*,
            m.img
        FROM
            m_product AS p
        LEFT JOIN
            m_productimg AS m ON p.id = m.product_id
        WHERE
            p.account_id = %s
        AND
            p.draft = 0
    """
    cur.execute(sql, (user_id,))
    products = cur.fetchall()

    # Most recent product
    sql = """
        SELECT
            p.*,
            m.img
        FROM
            m_product AS p
        LEFT JOIN
            m_productimg AS m ON p.id = m.product_id
        WHERE
            p.account_id = %s
        AND
            p.draft = 0
        ORDER BY p.id DESC
        LIMIT 1
    """
    cur.execute(sql, (user_id,))
    recent = cur.fetchone()

    cur.close()
    con.close()

    return render_template(
        'seller/seller_products.html',
        products=products,
        recent=recent,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Draft list page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/draft', methods=['GET'])
def seller_draft():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)

    sql = """
        SELECT
            p.*,
            m.img
        FROM
            m_product AS p
        LEFT JOIN
            m_productimg AS m ON p.id = m.product_id
        WHERE
            p.account_id = %s
        AND
            p.draft = 1
    """
    cur.execute(sql, (user_id,))
    products = cur.fetchall()

    sql = """
        SELECT
            p.*,
            m.img
        FROM
            m_product AS p
        LEFT JOIN
            m_productimg AS m ON p.id = m.product_id
        WHERE
            p.account_id = %s
        AND
            p.draft = 1
        ORDER BY p.id DESC
        LIMIT 1
    """
    cur.execute(sql, (user_id,))
    recent = cur.fetchone()

    cur.close()
    con.close()

    return render_template(
        'seller/seller_draft.html',
        products=products,
        recent=recent,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Product edit / update page
# ---------------------------------------------------------------------------
@seller_bp.route('/update/<int:product_id>', methods=['GET'])
def update(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    try:
        con = connect_db()
        cur = con.cursor(dictionary=True)

        sql = "SELECT * FROM m_product WHERE id = %s AND account_id = %s"
        cur.execute(sql, (product_id, user_id))
        product = cur.fetchone()

        if not product:
            cur.close()
            con.close()
            return redirect(url_for('seller.seller_products'))

        # Size data
        category2 = product.get('category_id')
        size_data = {}
        if category2 == 2:  # tops
            cur.execute("SELECT * FROM m_topssize WHERE product_id = %s", (product_id,))
            size_data = cur.fetchone() or {}
            session['active_tab'] = 'tops'
        else:              # bottoms
            cur.execute("SELECT * FROM m_bottomssize WHERE product_id = %s", (product_id,))
            size_data = cur.fetchone() or {}
            session['active_tab'] = 'bottoms'

        size_data['notes'] = product['size']

        # Laundry / clean signs
        cur.execute("SELECT cleanSign_id FROM t_clean WHERE product_id = %s", (product_id,))
        clean_results = cur.fetchall()
        clean_data = {}

        if clean_results:
            clean_sign_to_field = {
                'wash':      ['190', '170', '160', '161', '150', '151', '140', '141',
                               '142', '130', '131', '132', '110', '111', '100'],
                'bleach':    ['220', '210', '200'],
                'tumble':    ['320', '310', '300'],
                'dry':       ['440', '445', '430', '435', '420', '425', '410', '415'],
                'iron':      ['530', '520', '510', '511', '500'],
                'dryclean':  ['620', '621', '610', '611', '600'],
                'wet':       ['710', '711', '712', '700'],
            }
            for row in clean_results:
                sign_id = str(row['cleanSign_id'])
                for field_name, values in clean_sign_to_field.items():
                    if sign_id in values:
                        clean_data[field_name] = sign_id
                        break

        clean_data['note'] = product['cleanNotes']

        cur.close()
        con.close()

        session['size_selected'] = size_data
        session['clean_selected'] = clean_data
        session['edit_product_id'] = product_id
        session.modified = True

        return render_template('seller/seller_update.html', user_id=user_id, product=product)

    except Exception as e:
        print(f'エラー: {str(e)}')
        return redirect(url_for('seller.seller_products'))


# ---------------------------------------------------------------------------
# Size selection page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/size', methods=['GET'])
def seller_size():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    selected = session.get('size_selected', {})
    active_tab = session.get('active_tab', 'tops')
    return render_template(
        'seller/seller_size.html',
        selected=selected,
        active_tab=active_tab,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# Save size selection to session
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/size/success', methods=['POST'])
def seller_size_success():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    active_tab = request.form.get('active_tab', 'tops')
    session['active_tab'] = active_tab

    tops_fields    = ['shoulderWidth', 'bodyWidth', 'sleeveLength', 'bodyLength', 'notes']
    bottoms_fields = ['hip', 'totalLength', 'rise', 'inseam', 'waist',
                      'thighWidth', 'hemWidth', 'skirtLength', 'notes']

    size_data = request.form.to_dict()

    if active_tab == 'tops':
        filtered_data = {k: v for k, v in size_data.items() if k in tops_fields}
    else:
        filtered_data = {k: v for k, v in size_data.items() if k in bottoms_fields}

    session['size_selected'] = filtered_data
    return redirect(url_for('seller.seller_format'))


# ---------------------------------------------------------------------------
# Get size selection (AJAX)
# ---------------------------------------------------------------------------
@seller_bp.route('/get_size_selected')
def get_size_selected():
    return jsonify(session.get('size_selected', {}))


# ---------------------------------------------------------------------------
# Laundry / clean sign selection page
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/clean', methods=['GET'])
def seller_clean():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    selected = session.get('clean_selected', {})
    return render_template('seller/seller_clean.html', selected=selected, user_id=user_id)


# ---------------------------------------------------------------------------
# Save clean selection to session
# ---------------------------------------------------------------------------
@seller_bp.route('/seller/clean/success', methods=['POST'])
def seller_clean_success():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    session['clean_selected'] = request.form.to_dict()
    return redirect(url_for('seller.seller_format'))


# ---------------------------------------------------------------------------
# Get clean selection (AJAX)
# ---------------------------------------------------------------------------
@seller_bp.route('/get_clean_selected')
def get_clean_selected():
    return jsonify(session.get('clean_selected', {}))


# ---------------------------------------------------------------------------
# Save product to DB (publish)
# ---------------------------------------------------------------------------
@seller_bp.route('/format/save-product', methods=['POST'])
def save_product():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    try:
        product_data_str = request.form.get('productData')
        if not product_data_str:
            return jsonify({'success': False, 'message': '商品情報がありません'}), 400

        data = json.loads(product_data_str)

        con = connect_db()
        cursor = con.cursor()

        sql = """
            INSERT INTO m_product (
                name, purchasePrice, rentalPrice, size, color, `for`,
                upload, showing, draft, updateDate, purchaseFlg, rentalFlg,
                explanation, account_id, brand_id, category_id, cleanNotes,
                smokingFlg, returnAddress, `condition`, rentalPeriod
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        current_date     = datetime.now().date()
        current_datetime = datetime.now()

        values = (
            data.get('name'),
            int(data.get('purchasePrice')) if data.get('purchasePrice') else None,
            int(data.get('rentalPrice'))   if data.get('rentalPrice')   else None,
            session.get('size_selected', {}).get('notes'),
            data.get('color'),
            data.get('category1', 'ユニセックス'),
            current_date,
            '公開',
            1,
            current_datetime,
            1 if data.get('purchase') else 0,
            1 if data.get('rental')   else 0,
            data.get('explanation') or None,
            user_id,
            int(data.get('brand'))     if data.get('brand')     else None,
            int(data.get('category2')) if data.get('category2') else None,
            session.get('clean_selected', {}).get('notes'),
            1 if data.get('smoking') else 0,
            data.get('returnLocation') or None,
            '取引可',
            int(data.get('rentalPeriod')) if data.get('rentalPeriod') else None,
        )

        cursor.execute(sql, values)
        con.commit()
        product_id = cursor.lastrowid

        # --- Size registration ---
        size_selected = session.get('size_selected', {})
        category2 = data.get('category2')

        if category2 == '2':  # tops
            tops_sql = """
                INSERT INTO m_topssize
                    (product_id, shoulderWidth, bodyWidth, sleeveLength, bodyLength, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(tops_sql, (
                product_id,
                size_selected.get('shoulderWidth'),
                size_selected.get('bodyWidth'),
                size_selected.get('sleeveLength'),
                size_selected.get('bodyLength'),
                size_selected.get('notes'),
            ))
            con.commit()
        else:                  # bottoms
            bottoms_sql = """
                INSERT INTO m_bottomssize
                    (product_id, hip, totalLength, rise, inseam, waist,
                     thighWidth, hemWidth, skirtLength, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(bottoms_sql, (
                product_id,
                size_selected.get('hip'),
                size_selected.get('totalLength'),
                size_selected.get('rise'),
                size_selected.get('inseam'),
                size_selected.get('waist'),
                size_selected.get('thighWidth'),
                size_selected.get('hemWidth'),
                size_selected.get('skirtLength'),
                size_selected.get('notes'),
            ))
            con.commit()

        # --- Clean sign registration ---
        clean_selected = session.get('clean_selected', {})
        inserted_count = 0
        try:
            for key, val in clean_selected.items():
                if key == 'notes' or not val:
                    continue
                sql_clean = """
                    INSERT INTO t_clean (product_id, cleanSign_id)
                    VALUES (%s, %s)
                """
                cursor.execute(sql_clean, (product_id, val))
                inserted_count += 1
            con.commit()
        except Exception as e:
            print(f't_clean 登録エラー: {str(e)}')
            con.rollback()

        # --- Image upload ---
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_folder = 'app/static/img/productImg'
            os.makedirs(upload_folder, exist_ok=True)

            for index, file in enumerate(files):
                try:
                    if file and file.filename:
                        timestamp = int(datetime.now().timestamp() * 1000)
                        filename  = f'product_{product_id}_{index}_{timestamp}.png'
                        filepath  = os.path.join(upload_folder, filename)
                        file.save(filepath)

                        cursor.execute(
                            "INSERT INTO m_productimg (product_id, img) VALUES (%s, %s)",
                            (int(product_id), filename),
                        )
                        con.commit()
                except Exception as img_error:
                    print(f'画像{index}アップロード失敗: {str(img_error)}')
                    con.rollback()

        cursor.close()
        con.close()

        session.pop('size_selected',  None)
        session.pop('clean_selected', None)
        session.pop('edit_product_id', None)

        return jsonify({'success': True, 'message': 'DBの登録成功', 'product_id': product_id}), 200

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'DBエラー: {str(err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Save product to DB (draft)
# ---------------------------------------------------------------------------
@seller_bp.route('/format/save-product-draft', methods=['POST'])
def save_product_draft():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    try:
        product_data_str = request.form.get('productData')
        if not product_data_str:
            return jsonify({'success': False, 'message': '商品情報がありません'}), 400

        data = json.loads(product_data_str)

        con = connect_db()
        cursor = con.cursor()

        sql = """
            INSERT INTO m_product (
                name, purchasePrice, rentalPrice, rentalPeriod, size, color,
                `for`, upload, showing, draft, updateDate, purchaseFlg, rentalFlg,
                explanation, account_id, brand_id, category_id, cleanNotes,
                smokingFlg, returnAddress
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """

        current_date     = datetime.now().date()
        current_datetime = datetime.now()

        values = (
            data.get('name'),
            int(data.get('purchasePrice')) if data.get('purchasePrice') else None,
            int(data.get('rentalPrice'))   if data.get('rentalPrice')   else None,
            int(data.get('rentalPeriod'))  if data.get('rentalPeriod')  else None,
            session.get('size_selected', {}).get('notes'),
            data.get('color'),
            data.get('category1', 'ユニセックス'),
            current_date,
            '公開',
            1,
            current_datetime,
            1 if data.get('purchase') else 0,
            1 if data.get('rental')   else 0,
            data.get('explanation') or None,
            user_id,
            int(data.get('brand'))     if data.get('brand')     else None,
            int(data.get('category2')) if data.get('category2') else None,
            session.get('clean_selected', {}).get('notes'),
            1 if data.get('smoking') else 0,
            data.get('returnLocation') or None,
        )

        cursor.execute(sql, values)
        con.commit()
        product_id = cursor.lastrowid

        # --- Clean sign registration ---
        clean_selected = session.get('clean_selected', {})
        try:
            for key, val in clean_selected.items():
                if key == 'notes' or not val:
                    continue
                cursor.execute(
                    "INSERT INTO t_clean (product_id, cleanSign_id) VALUES (%s, %s)",
                    (product_id, val),
                )
                inserted_count = 0
                inserted_count += 1
            con.commit()
        except Exception as e:
            print(f't_clean 登録エラー: {str(e)}')
            con.rollback()

        # --- Image upload ---
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_folder = 'app/static/img/productImg'
            os.makedirs(upload_folder, exist_ok=True)

            for index, file in enumerate(files):
                try:
                    if file and file.filename:
                        timestamp = int(datetime.now().timestamp() * 1000)
                        filename  = f'product_{product_id}_{index}_{timestamp}.png'
                        filepath  = os.path.join(upload_folder, filename)
                        file.save(filepath)

                        cursor.execute(
                            "INSERT INTO m_productimg (product_id, img) VALUES (%s, %s)",
                            (int(product_id), filename),
                        )
                        con.commit()
                except Exception as img_error:
                    print(f'画像{index}アップロード失敗: {str(img_error)}')
                    con.rollback()

        cursor.close()
        con.close()

        session.pop('size_selected',  None)
        session.pop('clean_selected', None)

        return jsonify({'success': True, 'message': '下書きDBの登録成功', 'product_id': product_id}), 200

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'DBエラー: {str(err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Update existing product
# ---------------------------------------------------------------------------
@seller_bp.route('/format/update-product', methods=['POST'])
def update_product():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id        = session.get('user_id')
    edit_product_id = session.get('edit_product_id')

    try:
        product_data_str = request.form.get('productData')
        if not product_data_str:
            return jsonify({'success': False, 'message': '商品情報がありません'}), 400

        data = json.loads(product_data_str)

        con    = connect_db()
        cursor = con.cursor()

        if edit_product_id:
            sql = """
                UPDATE m_product
                SET
                    name          = %s,
                    purchasePrice = %s,
                    rentalPrice   = %s,
                    rentalPeriod  = %s,
                    color         = %s,
                    explanation   = %s,
                    purchaseFlg   = %s,
                    rentalFlg     = %s,
                    smokingFlg    = %s,
                    returnAddress = %s,
                    updateDate    = %s
                WHERE id = %s AND account_id = %s
            """
            values = (
                data.get('name'),
                int(data.get('purchasePrice')) if data.get('purchasePrice') else None,
                int(data.get('rentalPrice'))   if data.get('rentalPrice')   else None,
                int(data.get('rentalPeriod'))  if data.get('rentalPeriod')  else None,
                data.get('color'),
                data.get('explanation') or None,
                1 if data.get('purchase') else 0,
                1 if data.get('rental')   else 0,
                1 if data.get('smoking')  else 0,
                data.get('returnLocation') or None,
                datetime.now(),
                edit_product_id,
                user_id,
            )
            cursor.execute(sql, values)
            con.commit()
            product_id = edit_product_id

        else:
            sql = """
                INSERT INTO m_product (
                    name, purchasePrice, rentalPrice, rentalPeriod, size, color,
                    `for`, upload, showing, draft, updateDate, purchaseFlg, rentalFlg,
                    explanation, account_id, brand_id, category_id, cleanNotes,
                    smokingFlg, returnAddress
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """
            current_date     = datetime.now().date()
            current_datetime = datetime.now()

            values = (
                data.get('name'),
                int(data.get('purchasePrice')) if data.get('purchasePrice') else None,
                int(data.get('rentalPrice'))   if data.get('rentalPrice')   else None,
                int(data.get('rentalPeriod'))  if data.get('rentalPeriod')  else None,
                session.get('size_selected', {}).get('notes'),
                data.get('color'),
                data.get('category1', 'ユニセックス'),
                current_date,
                '公開',
                0,
                current_datetime,
                1 if data.get('purchase') else 0,
                1 if data.get('rental')   else 0,
                data.get('explanation') or None,
                user_id,
                int(data.get('brand'))     if data.get('brand')     else None,
                int(data.get('category2')) if data.get('category2') else None,
                session.get('clean_selected', {}).get('notes'),
                1 if data.get('smoking') else 0,
                data.get('returnLocation') or None,
            )
            cursor.execute(sql, values)
            con.commit()
            product_id = cursor.lastrowid

        # --- Image upload ---
        if 'images' in request.files:
            files = request.files.getlist('images')
            upload_folder = 'app/static/img/productImg'
            os.makedirs(upload_folder, exist_ok=True)

            for index, file in enumerate(files):
                try:
                    if file and file.filename:
                        timestamp = int(datetime.now().timestamp() * 1000)
                        filename  = f'product_{product_id}_{index}_{timestamp}.png'
                        filepath  = os.path.join(upload_folder, filename)
                        file.save(filepath)

                        cursor.execute(
                            "INSERT INTO m_productimg (product_id, img) VALUES (%s, %s)",
                            (int(product_id), filename),
                        )
                        con.commit()
                except Exception as img_error:
                    print(f'画像{index}アップロード失敗: {str(img_error)}')
                    con.rollback()

        cursor.close()
        con.close()

        session.pop('size_selected',  None)
        session.pop('clean_selected', None)
        session.pop('edit_product_id', None)

        return jsonify({'success': True, 'message': 'DBの登録成功', 'product_id': product_id}), 200

    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': f'DBエラー: {str(err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Delete product
# ---------------------------------------------------------------------------
@seller_bp.route('/format/delete-product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'ログインが必要です'}), 401

    user_id = session.get('user_id')

    try:
        con    = connect_db()
        cursor = con.cursor(dictionary=True)

        sql = """
            SELECT t.status
            FROM m_product AS p
            LEFT JOIN t_transaction AS t ON p.id = t.product_id
            WHERE p.id = %s
            LIMIT 1
        """
        cursor.execute(sql, (product_id,))
        status_row = cursor.fetchone()

        # Allow deletion when no transaction exists or when transaction is complete
        can_delete = (
            status_row is None
            or status_row.get('status') is None
            or status_row.get('status') == '取引完了'
        )

        if can_delete:
            cursor.execute("DELETE FROM m_productimg   WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM m_topssize     WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM m_bottomssize  WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM t_clean        WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM t_comments     WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM m_product      WHERE id         = %s", (product_id,))
            con.commit()
        else:
            cursor.close()
            con.close()
            return jsonify({'success': False, 'message': '取引中は削除できません'}), 400

        cursor.close()
        con.close()
        return jsonify({'success': True, 'message': '商品を削除しました'}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'エラー: {str(e)}'}), 500
