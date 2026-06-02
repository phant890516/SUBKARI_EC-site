# ==========================================================
# Filename      : app/views/products.py
# Descriptions  : Product listing, detail, purchase, rental
# ==========================================================
from flask import (Blueprint, render_template, request, make_response,
                   session, redirect, url_for, jsonify)
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import mysql.connector
import json
import os
import random

products_bp = Blueprint('products', __name__, url_prefix='/products')


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
# Helper: get product info
# ---------------------------------------------------------------------------
def get_product_info(product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    sql = """
        SELECT
            p.*,
            b.name AS brand_name,
            c.name AS category_name
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE p.id = %s
    """
    cur.execute(sql, (product_id,))
    product = cur.fetchone()
    cur.close()
    con.close()
    return product


# ---------------------------------------------------------------------------
# Helper: get product images
# ---------------------------------------------------------------------------
def get_product_images(product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT img FROM m_productimg WHERE product_id = %s ORDER BY id ASC", (product_id,))
    images = cur.fetchall()
    cur.close()
    con.close()
    return images


# ---------------------------------------------------------------------------
# Helper: get seller transaction summary
# ---------------------------------------------------------------------------
def get_transaction_info(account_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)

    cur.execute(
        "SELECT AVG(score) AS 評価 FROM t_evaluation WHERE recipient_id = %s GROUP BY recipient_id",
        (account_id,),
    )
    evaluation = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) AS 評価件数 FROM t_evaluation WHERE recipient_id = %s GROUP BY recipient_id",
        (account_id,),
    )
    evaluationCount = cur.fetchone()

    cur.close()
    con.close()

    if evaluation:
        raw = evaluation.get('評価')
        evaluation['評価'] = round(float(raw), 1) if raw else None

    return evaluation, evaluationCount


# ---------------------------------------------------------------------------
# Helper: get user info
# ---------------------------------------------------------------------------
def get_user_info(account_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM m_account WHERE id = %s", (account_id,))
    user_info = cur.fetchone()
    cur.close()
    con.close()
    return user_info


# ---------------------------------------------------------------------------
# Helper: get comments
# ---------------------------------------------------------------------------
def get_comments(product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    sql = """
        SELECT
            t.content    AS text,
            m.username   AS user_name,
            t.account_id AS comment_account_id,
            t.createdDate
        FROM t_comments t
        JOIN m_account m ON t.account_id = m.id
        WHERE t.product_id = %s
        ORDER BY t.createdDate ASC
    """
    cur.execute(sql, (product_id,))
    rows = cur.fetchall()
    cur.close()
    con.close()
    return rows


# ---------------------------------------------------------------------------
# Helper: get tops size
# ---------------------------------------------------------------------------
def get_topsSize(product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute(
        "SELECT shoulderWidth, bodyWidth, sleeveLength, bodyLength, notes "
        "FROM m_topsSize WHERE product_id = %s",
        (product_id,),
    )
    result = cur.fetchone()
    cur.close()
    con.close()
    return result


# ---------------------------------------------------------------------------
# Helper: get bottoms size
# ---------------------------------------------------------------------------
def get_bottomsSize(product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute(
        "SELECT hip, totalLength, rise, inseam, waist, "
        "thighWidth, hemWidth, skirtLength, notes "
        "FROM m_bottomsSize WHERE product_id = %s",
        (product_id,),
    )
    result = cur.fetchone()
    cur.close()
    con.close()
    return result


# ---------------------------------------------------------------------------
# Helper: calculate rental price
# ---------------------------------------------------------------------------
def calculate_rental_price(product_id):
    product = get_product_info(product_id)
    if not product:
        return {}

    rental_price  = product.get('rentalPrice')  or 0
    rental_period = product.get('rentalPeriod') or 0

    return {
        'rentalPrice':  rental_price,
        'rentalPeriod': rental_period,
        'totalPrice':   rental_price * rental_period,
    }


# ---------------------------------------------------------------------------
# Helper: other products by same seller
# ---------------------------------------------------------------------------
def get_other_products_images(seller_id, current_product_id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    sql = """
        SELECT
            i.img,
            p.id AS product_id
        FROM m_productImg i
        INNER JOIN (
            SELECT product_id, MIN(id) AS first_image_id
            FROM m_productImg
            GROUP BY product_id
        ) AS first_img ON i.id = first_img.first_image_id
        INNER JOIN m_product p ON p.id = i.product_id
        WHERE p.account_id = %s AND p.id != %s
        LIMIT 6
    """
    cur.execute(sql, (seller_id, current_product_id))
    results = cur.fetchall()
    cur.close()
    con.close()
    return results


# ---------------------------------------------------------------------------
# Helper: recommended products
# ---------------------------------------------------------------------------
def get_recommended_products(product_id):
    product = get_product_info(product_id)
    if not product:
        return [], 'デフォルト'

    con = connect_db()
    cur = con.cursor(dictionary=True)

    category_id = product.get('category_id')
    sql = """
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        WHERE p.category_id = %s
        AND p.id != %s
        AND p.draft = 0
        ORDER BY RAND()
        LIMIT 6
    """
    cur.execute(sql, (category_id, product_id))
    recommended_products = cur.fetchall()
    cur.close()
    con.close()

    logic_name = 'カテゴリ別おすすめ'
    return recommended_products, logic_name


# ---------------------------------------------------------------------------
# Helper: follow / connection info
# ---------------------------------------------------------------------------
def get_connection(target_id):
    user_id = session.get('user_id')
    if not user_id:
        return None

    con = None
    try:
        con = connect_db()
        cur = con.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM t_connection "
            "WHERE execution_id = %s AND target_id = %s AND type = 'フォロー'",
            (user_id, target_id),
        )
        connection = cur.fetchone()
    except mysql.connector.Error as err:
        print(f'データベースエラー: {err}')
        connection = None
    finally:
        if con and con.is_connected():
            cur.close()
            con.close()

    return connection


# ---------------------------------------------------------------------------
# Search results page
# ---------------------------------------------------------------------------
@products_bp.route('/search_result', methods=['GET'])
def search_result():
    user_id  = session.get('user_id')
    products = []

    con = None
    try:
        con = connect_db()
        cur = con.cursor(dictionary=True)
        # Use actual column names from m_product
        sql = """
            SELECT
                p.id,
                p.name,
                b.name AS brand,
                p.rentalPrice,
                p.purchasePrice,
                (
                    SELECT m2.img
                    FROM m_productimg AS m2
                    WHERE m2.product_id = p.id
                    ORDER BY m2.id ASC
                    LIMIT 1
                ) AS image_path
            FROM m_product AS p
            LEFT JOIN m_brand AS b ON p.brand_id = b.id
            WHERE p.draft = 0
            LIMIT 50
        """
        cur.execute(sql)
        products = cur.fetchall()
        cur.close()
    except mysql.connector.Error as err:
        print(f'DB Error: {err}')
    finally:
        if con and con.is_connected():
            con.close()

    return make_response(render_template(
        'top/search_product.html',
        user_id=user_id,
        products=products,
    ))


# ---------------------------------------------------------------------------
# Product detail page
# ---------------------------------------------------------------------------
@products_bp.route('/<int:product_id>', methods=['GET'])
def product_details_stub(product_id):
    user_id  = session.get('user_id')
    product  = None
    comments = []
    con      = None
    cur      = None

    try:
        con = connect_db()
        cur = con.cursor(dictionary=True)

        product = get_product_info(product_id)
        if not product:
            return render_template('error.html'), 404

        images = get_product_images(product_id)

        # Comments
        sql_comments = """
            SELECT
                t.content    AS text,
                m.username   AS user_name,
                t.account_id AS comment_account_id,
                t.createdDate
            FROM t_comments t
            JOIN m_account m ON t.account_id = m.id
            WHERE t.product_id = %s
            ORDER BY t.createdDate ASC
        """
        cur.execute(sql_comments, (product_id,))
        fetched_comments = cur.fetchall()

        seller_id = int(product['account_id'])
        for comment in fetched_comments:
            is_seller = (comment['comment_account_id'] == seller_id)
            comments.append({
                'user_name':    comment['user_name'],
                'text':         comment['text'],
                'is_seller':    is_seller,
                'created_date': (
                    comment['createdDate'].strftime('%Y/%m/%d %H:%M')
                    if comment['createdDate'] else ''
                ),
            })

        # Size info
        topSize     = get_topsSize(product_id)
        bottomsSize = get_bottomsSize(product_id)

    except mysql.connector.Error as err:
        print(f'データベースエラー: {err}')
    finally:
        if con and con.is_connected():
            cur.close()
            con.close()

    calculated_prices      = calculate_rental_price(product_id)
    evaluation, evaluationCount = get_transaction_info(product['account_id'])
    seller_info            = get_user_info(product['account_id'])
    other_products_images  = get_other_products_images(
        seller_id=product['account_id'], current_product_id=product_id
    )
    recommended_products, logic_name = get_recommended_products(product_id)

    connection = get_connection(product['account_id']) if user_id else None

    return make_response(render_template(
        'products/product_details.html',
        user_id=user_id,
        product=product,
        images=images,
        comments=comments,
        calculated_prices=calculated_prices,
        evaluation=evaluation,
        evaluationCount=evaluationCount,
        seller_info=seller_info,
        topSize=topSize,
        bottomsSize=bottomsSize,
        other_products_images=other_products_images,
        recommended_products=recommended_products,
        logic_name=logic_name,
        connection=connection,
        error_message='',
    ))


# ---------------------------------------------------------------------------
# Rental selection page
# ---------------------------------------------------------------------------
@products_bp.route('/rental/<int:product_id>', methods=['GET'])
def rental(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    product = get_product_info(product_id)

    if not product:
        return render_template('error.html'), 404
    if product.get('condition') in ('取引中', '売却済み'):
        return render_template('error.html'), 404
    if not product.get('rentalFlg'):
        return redirect(url_for('products.product_details_stub', product_id=product_id))

    images           = get_product_images(product_id)
    calculated_prices = calculate_rental_price(product_id)
    topSize          = get_topsSize(product_id)
    bottomsSize      = get_bottomsSize(product_id)

    return render_template(
        'purchase/rental.html',
        user_id=user_id,
        product=product,
        images=images,
        calculated_prices=calculated_prices,
        topSize=topSize,
        bottomsSize=bottomsSize,
    )


# ---------------------------------------------------------------------------
# Purchase selection page
# ---------------------------------------------------------------------------
@products_bp.route('/purchase/<int:product_id>', methods=['GET'])
def purchase(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    product = get_product_info(product_id)

    if not product:
        return render_template('error.html'), 404
    if product.get('condition') in ('取引中', '売却済み'):
        return render_template('error.html'), 404
    if not product.get('purchaseFlg'):
        return redirect(url_for('products.product_details_stub', product_id=product_id))

    images = get_product_images(product_id)

    return render_template(
        'purchase/purchase.html',
        user_id=user_id,
        product=product,
        images=images,
    )


# ---------------------------------------------------------------------------
# Transaction complete page (purchase)
# ---------------------------------------------------------------------------
@products_bp.route('/transaction_complete', methods=['POST'])
def transaction_complete():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    addressId      = request.form.get('addressId')
    seller_id      = request.form.get('seller_id')
    product_id     = request.form.get('product_id')
    status         = request.form.get('status', '支払い待ち')
    situation      = request.form.get('situation', '購入')
    payment_method = request.form.get('paymentMethod', 'クレジットカード')
    creditcard_id  = request.form.get('creditcard_id')
    shipping_flg   = False
    received_flg   = False

    paymentDeadline = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')

    con = None
    try:
        con = connect_db()
        cur = con.cursor(dictionary=True)

        cur.execute(
            "SELECT pref, address1, address2, address3 FROM m_address WHERE id = %s",
            (addressId,),
        )
        address = cur.fetchone()
        shippingAddress = (
            f"{address['pref']} {address['address1']} "
            f"{address['address2']} {address['address3']}"
        ) if address else ''

        cur.execute("""
            INSERT INTO t_transaction (
                customer_id, seller_id, product_id, status, situation,
                paymentMethod, paymentDeadline, shippingAddress,
                creditcard_id, shippingFlg, receivedFlg
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, seller_id, product_id, status, situation,
            payment_method, paymentDeadline, shippingAddress,
            creditcard_id, shipping_flg, received_flg,
        ))
        con.commit()

        cur.execute(
            "UPDATE m_product SET `condition` = '取引中' WHERE id = %s",
            (product_id,),
        )
        con.commit()

    except mysql.connector.Error as err:
        print(f'データベースエラー: {err}')
    finally:
        if con and con.is_connected():
            cur.close()
            con.close()

    return render_template('purchase/transaction_complete.html', user_id=user_id)


# ---------------------------------------------------------------------------
# Rental complete page
# ---------------------------------------------------------------------------
@products_bp.route('/rental_complete', methods=['POST'])
def rental_complete():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')
    return render_template('purchase/rental_complete.html', user_id=user_id)
