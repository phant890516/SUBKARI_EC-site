# ==========================================================
# Filename      : app/views/top.py
# Descriptions  : Top / index pages, category / search pages
# ==========================================================
from flask import (Blueprint, render_template, request, make_response,
                   redirect, url_for, session)
import mysql.connector
import math
import os

top_bp = Blueprint('top', __name__)


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
# Helper: build price display string
# ---------------------------------------------------------------------------
def _price_text(row):
    rental   = row.get('rentalPrice')
    purchase = row.get('purchasePrice')
    if rental is not None and purchase is not None:
        return f'{rental:,} / {purchase:,}'
    if rental is not None:
        return f'{rental:,}'
    if purchase is not None:
        return f'{purchase:,}'
    return 'ー'


# ---------------------------------------------------------------------------
# Helper: build category dict from rows
# ---------------------------------------------------------------------------
def _build_categories(rows, limit=4):
    categories = {}
    for row in rows:
        cat = row.get('category') or 'その他'
        if cat not in categories:
            categories[cat] = []
        if limit is None or len(categories[cat]) < limit:
            categories[cat].append({
                'id':         row['id'],
                'name':       row['name'],
                'brand':      row.get('brand') or '',
                'price':      _price_text(row),
                'image_path': row.get('image_path') or 'default.png',
            })
    return categories


# ---------------------------------------------------------------------------
# Guest top page
# ---------------------------------------------------------------------------
@top_bp.route('/')
def guest_index():
    if 'user_id' in session:
        return redirect(url_for('top.member_index'))

    user_id = None

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            c.name AS category,
            b.name AS brand,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE p.draft = 0
        GROUP BY p.id
        ORDER BY p.category_id, p.id
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()

    categories = _build_categories(rows, limit=4)
    return render_template('top/guest_index.html', user_id=user_id, categories=categories)


# ---------------------------------------------------------------------------
# Member top page
# ---------------------------------------------------------------------------
@top_bp.route('/top', methods=['GET'])
def member_index():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            c.name AS category,
            b.name AS brand,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE p.draft = 0
        GROUP BY p.id
        ORDER BY p.category_id, p.id
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()

    categories = _build_categories(rows, limit=4)
    return render_template('top/member_index.html', categories=categories, user_id=user_id)


# ---------------------------------------------------------------------------
# Category products page
# ---------------------------------------------------------------------------
@top_bp.route('/category/<category>', methods=['GET'])
def category_products(category):
    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            b.name AS brand,
            c.name AS category,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE c.name = %s
        AND p.draft = 0
        ORDER BY p.id DESC
    """, (category,))
    rows = cur.fetchall()
    cur.close()
    con.close()

    products = [
        {
            'id':         row['id'],
            'name':       row['name'],
            'brand':      row.get('brand') or '',
            'price':      _price_text(row),
            'image_path': row.get('image_path') or 'default.png',
        }
        for row in rows
    ]
    categories = {category: products}

    return render_template(
        'top/member_index.html',
        categories=categories,
        user_id=user_id,
        single_category=True,
    )


# ---------------------------------------------------------------------------
# Gender (for) products page
# ---------------------------------------------------------------------------
@top_bp.route('/for/<for_value>', methods=['GET'])
def for_products(for_value):
    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            p.`for`,
            c.name AS category,
            b.name AS brand,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE p.`for` = %s
        AND p.draft = 0
    """, (for_value,))
    rows = cur.fetchall()
    cur.close()
    con.close()

    categories = _build_categories(rows, limit=None)
    return render_template(
        'top/member_index.html',
        categories=categories,
        user_id=user_id,
        selected_for=for_value,
        single_category=True,
    )


# ---------------------------------------------------------------------------
# Brand products page
# ---------------------------------------------------------------------------
@top_bp.route('/brand/<brand_name>', methods=['GET'])
def brand_products(brand_name):
    user_id = session.get('user_id')

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.id,
            p.name,
            p.rentalPrice,
            p.purchasePrice,
            c.name AS category,
            b.name AS brand,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS image_path
        FROM m_product AS p
        LEFT JOIN m_brand    AS b ON p.brand_id    = b.id
        LEFT JOIN m_category AS c ON p.category_id = c.id
        WHERE b.name = %s
        AND p.draft = 0
    """, (brand_name,))
    rows = cur.fetchall()
    cur.close()
    con.close()

    categories = _build_categories(rows, limit=None)
    return render_template(
        'top/member_index.html',
        categories=categories,
        user_id=user_id,
        selected_brand=brand_name,
    )


# ---------------------------------------------------------------------------
# Search results page
# ---------------------------------------------------------------------------
@top_bp.route('/search', methods=['GET'])
def search():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))

    user_id      = session.get('user_id')
    search_query = request.args.get('keyword', '').strip()
    page         = int(request.args.get('page', 1))
    limit        = 5
    offset       = (page - 1) * limit

    con = connect_db()
    cur = con.cursor(dictionary=True)

    # Count
    cur.execute("""
        SELECT COUNT(DISTINCT p.id) AS count
        FROM m_product AS p
        WHERE (%s = '' OR p.name LIKE %s)
        AND p.draft = 0
    """, (search_query, f'%{search_query}%'))
    result      = cur.fetchone()
    total_count = int(result['count']) if result else 0
    cur.close()
    con.close()

    total_pages = math.ceil(total_count / limit) if total_count else 1

    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT
            p.*,
            b.name AS brand_name,
            (
                SELECT m2.img
                FROM m_productimg AS m2
                WHERE m2.product_id = p.id
                ORDER BY m2.id ASC
                LIMIT 1
            ) AS img
        FROM m_product AS p
        LEFT JOIN m_brand AS b ON p.brand_id = b.id
        WHERE (%s = '' OR p.name LIKE %s)
        AND p.draft = 0
        GROUP BY p.id
        ORDER BY p.id DESC
        LIMIT %s OFFSET %s
    """, (search_query, f'%{search_query}%', limit, offset))
    products = cur.fetchall()
    cur.close()
    con.close()

    for p in products:
        rental   = p.get('rentalPrice')
        purchase = p.get('purchasePrice')
        if rental is not None and purchase is not None:
            p['price'] = f'{rental:,} / {purchase:,}'
        elif rental is not None:
            p['price'] = rental
        elif purchase is not None:
            p['price'] = purchase
        else:
            p['price'] = 0

    return render_template(
        'top/search_product.html',
        search_query=search_query,
        products=products,
        total_pages=total_pages,
        current_page=page,
        user_id=user_id,
    )


# ---------------------------------------------------------------------------
# About Subkari page
# ---------------------------------------------------------------------------
@top_bp.route('/about_subkari', methods=['GET'])
def about_subkari():
    user_id = session.get('user_id')
    return make_response(render_template('top/welcome_subkari.html', user_id=user_id))


# ---------------------------------------------------------------------------
# Tops / Bottoms / Accessories / Coordinate category shortcuts
# These now query the DB instead of returning dummy data.
# ---------------------------------------------------------------------------
@top_bp.route('/tops', methods=['GET'])
def tops():
    return redirect(url_for('top.category_products', category='トップス'))


@top_bp.route('/bottoms', methods=['GET'])
def bottoms():
    return redirect(url_for('top.category_products', category='ボトムス'))


@top_bp.route('/accessories', methods=['GET'])
def accessories():
    return redirect(url_for('top.category_products', category='アクセサリー'))


@top_bp.route('/coordinate', methods=['GET'])
def coordinate():
    user_id = session.get('user_id')
    return render_template('top/search_product.html', search_query=None,
                           products=[], user_id=user_id)


# ---------------------------------------------------------------------------
# Product details stub (redirects to products blueprint)
# ---------------------------------------------------------------------------
@top_bp.route('/product_details', methods=['GET'])
def product_details():
    user_id = session.get('user_id')
    return make_response(render_template('products/search_product.html', user_id=user_id))
