# ==========================================================
# Filename      : app/views/brand_serach.py
# Descriptions  : Brand search / brand-specific pages
# ==========================================================
from flask import render_template, Blueprint
import mysql.connector
import os

brand_serach_bp = Blueprint('brand_serach', __name__, url_prefix='/brand')


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
# TRAVAS TOKYO brand page
# ---------------------------------------------------------------------------
@brand_serach_bp.route('/TRAVASTOKYO')
def TRAVASTOKYO():
    con = connect_db()
    cur = con.cursor(dictionary=True)

    cur.execute("""
        SELECT
            p.id   AS product_id,
            p.name AS product_name,
            p.rentalPrice,
            p.`for`,
            (
                SELECT i.img
                FROM m_productImg AS i
                WHERE i.product_id = p.id
                ORDER BY i.img ASC
                LIMIT 1
            ) AS img
        FROM m_product AS p
        WHERE p.brand_id = 1
    """)

    rows = cur.fetchall()
    cur.close()
    con.close()

    return render_template('brand/TRAVASTOKYO.html', rows=rows)
