# ==========================================================
# Filename      : app/views/dashboard.py
# Descriptions  : Admin dashboard
# ==========================================================
from flask import render_template, Blueprint
import mysql.connector
import os

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


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
# Dashboard page
# ---------------------------------------------------------------------------
@dashboard_bp.route('/dashboard')
def dashboard():
    con = connect_db()
    cur = con.cursor(dictionary=True)

    cur.execute('SELECT * FROM v_weekly_new_users;')
    new_users = cur.fetchall()

    cur.execute('SELECT * FROM v_compare_1_week_ago_new_users;')
    users_compare = cur.fetchall()

    cur.execute('SELECT * FROM v_weekly_listing;')
    weekly_listing = cur.fetchall()

    cur.execute('SELECT * FROM v_compare_1_week_ago_listing;')
    listing_compare = cur.fetchall()

    cur.execute('SELECT * FROM v_weekly_active_users;')
    WAU = cur.fetchall()

    cur.execute('SELECT * FROM v_monthly_active_users;')
    MAU = cur.fetchall()

    cur.execute('SELECT * FROM v_alert_unchecked;')
    alert_unchecked = cur.fetchall()

    cur.execute('SELECT * FROM v_inquiry_unchecked;')
    inquiry_unchecked = cur.fetchall()

    cur.execute('SELECT * FROM v_identify_offer;')
    identify_offer = cur.fetchall()

    cur.execute('SELECT * FROM v_region_new_users;')
    region_new_users = cur.fetchall()

    cur.close()
    con.close()

    return render_template(
        'dashboard/dashboard.html',
        new_users=new_users,
        users_compare=users_compare,
        weekly_listing=weekly_listing,
        listing_compare=listing_compare,
        WAU=WAU,
        MAU=MAU,
        alert_unchecked=alert_unchecked,
        inquiry_unchecked=inquiry_unchecked,
        identify_offer=identify_offer,
        region_new_users=region_new_users,
    )
