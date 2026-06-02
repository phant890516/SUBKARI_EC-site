# ==========================================================
# Filename      : app/views/userprf.py
# Descriptions  : User profile pages
# ==========================================================
from flask import Blueprint, render_template, request, redirect, url_for, session
import mysql.connector
import os

userprf_bp = Blueprint('userprf', __name__, url_prefix='/userprf')


def connect_db():
    con = mysql.connector.connect(
        host=os.environ.get('AIVEN_DB_HOST'),
        user=os.environ.get('AIVEN_DB_USER'),
        passwd=os.environ.get('AIVEN_DB_PASSWORD'),
        db='db_subkari',
        port=os.environ.get('AIVEN_DB_PORT'),
        ssl_ca='ca.pem',
        ssl_disabled=False
    )
    return con


def get_user_info(id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM m_account WHERE id = %s", (id,))
    user_info = cur.fetchone()
    cur.close(); con.close()
    return user_info


def get_transaction_info(id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT count(*) AS フォロー数 FROM t_connection WHERE execution_id=%s AND type='フォロー' GROUP BY execution_id", (id,))
    follows = cur.fetchone()
    cur.execute("SELECT count(*) AS フォロワー数 FROM t_connection WHERE target_id=%s AND type='フォロー' GROUP BY target_id", (id,))
    followers = cur.fetchone()
    cur.execute("SELECT avg(score) AS 評価 FROM t_evaluation WHERE recipient_id=%s GROUP BY recipient_id", (id,))
    evaluation = cur.fetchone()
    cur.execute("SELECT count(*) AS 評価件数 FROM t_evaluation WHERE recipient_id=%s GROUP BY recipient_id", (id,))
    evaluationCount = cur.fetchone()
    cur.execute("SELECT count(*) AS 出品数 FROM m_product WHERE account_id=%s", (id,))
    products = cur.fetchone()
    cur.close(); con.close()
    if followers is None:   followers   = {'フォロワー数': 0}
    if follows is None:     follows     = {'フォロー数': 0}
    if products is None:    products    = {'出品数': 0}
    if evaluation is not None:
        evaluation['評価'] = round(float(evaluation['評価']))
    else:
        evaluation = {'評価': 0}
    return evaluation, evaluationCount, follows, followers, products


def get_product_info(id):
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT id FROM m_product WHERE account_id=%s", (id,))
    product_id = cur.fetchall()
    cur.execute("SELECT name FROM m_product WHERE account_id=%s", (id,))
    name = cur.fetchall()
    cur.execute("""
        SELECT i.* FROM m_productImg i
        INNER JOIN (SELECT product_id, MIN(id) AS first_image_id FROM m_productImg GROUP BY product_id) AS first_img ON i.id = first_img.first_image_id
        INNER JOIN m_product p ON p.id = i.product_id
        WHERE p.account_id = %s
    """, (id,))
    img = cur.fetchall()
    cur.close(); con.close()
    return product_id, name, img


@userprf_bp.route('/userprf', methods=['POST', 'GET'])
def userprf():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    id = request.form.get('id')
    user_info = get_user_info(id)
    evaluation, evaluationCount, follows, followers, products = get_transaction_info(id)
    productId, productName, productImg = get_product_info(id)
    return render_template("userprf/userprf.html",
                           evaluation=evaluation, evaluationCount=evaluationCount,
                           follows=follows, followers=followers, products=products,
                           productId=productId, productName=productName, productImg=productImg,
                           user_info=user_info, user_id=user_id)
