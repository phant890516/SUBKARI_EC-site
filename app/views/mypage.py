# ==========================================================
# Filename      : app/views/mypage.py
# Descriptions  : My page, profile, bank, likes, follow
# ==========================================================
from flask import Blueprint, render_template, request, make_response, redirect, url_for, session
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import mysql.connector
import json
import os

mypage_bp = Blueprint('mypage', __name__, url_prefix='/mypage')


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


def comma(num):
    if num == 0:
        return '0'
    return f'{int(num):,}'


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
        evaluation['評価'] = round(float(evaluation['評価']), 1)
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


def getAccountInfo():
    accountNumbers = []
    id = session['user_id']
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT bankName, accountNumber, branchCode FROM t_transfer WHERE account_id=%s LIMIT 3", (id,))
    bank_info = cur.fetchall()
    cur.close(); con.close()
    count = len(bank_info)
    for i in range(count):
        num = int(bank_info[i]['accountNumber'])
        length = len(str(num))
        mask = '*' * (length - 3)
        accountNumbers.append(mask + str(num % 1000))
    return bank_info, accountNumbers, count


@mypage_bp.route('/mypage')
def mypage():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    user_info = get_user_info(user_id)
    evaluation, evaluationCount, follows, followers, products = get_transaction_info(user_id)
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, ti.created_at,
               CASE WHEN t.situation='購入' THEN p.purchasePrice ELSE p.rentalPrice END AS price
        FROM t_transaction t
        INNER JOIN m_product p ON t.product_id = p.id
        LEFT JOIN t_time ti ON t.id = ti.transaction_id
        WHERE t.status='取引完了' AND p.account_id=%s
        GROUP BY ti.created_at, t.seller_id
    """, (user_id,))
    sales = cur.fetchall()
    cur.close(); con.close()
    total = comma(sum(int(s['price'] or 0) for s in sales))
    return render_template("mypage/mypage.html",
                           evaluation=evaluation, evaluationCount=evaluationCount,
                           follows=follows, followers=followers, products=products,
                           user_info=user_info, user_id=user_id, total=total)


@mypage_bp.route('/editProfile')
def editProfile():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    user_info = get_user_info(user_id)
    evaluation, evaluationCount, follows, followers, products = get_transaction_info(user_id)
    productId, productName, productImg = get_product_info(user_id)
    return render_template("mypage/editProfile.html",
                           evaluation=evaluation, evaluationCount=evaluationCount,
                           follows=follows, followers=followers, products=products,
                           productId=productId, productName=productName, productImg=productImg,
                           user_info=user_info, user_id=user_id)


@mypage_bp.route('/updateProfile', methods=['POST'])
def updateProfile():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    new_profile = request.form
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("UPDATE m_account SET username=%s, smoker=%s, introduction=%s WHERE id=%s",
                (new_profile['username'], new_profile['smoker'], new_profile['introduction'], user_id))
    con.commit()
    cur.close(); con.close()
    user_info = get_user_info(user_id)
    evaluation, evaluationCount, follows, followers, products = get_transaction_info(user_id)
    productId, productName, productImg = get_product_info(user_id)
    return render_template("mypage/editProfile.html",
                           user_info=user_info, evaluation=evaluation, evaluationCount=evaluationCount,
                           follows=follows, followers=followers, products=products,
                           productId=productId, productName=productName, productImg=productImg,
                           user_id=user_id)


@mypage_bp.route('/edit')
def edit():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    user_info = get_user_info(user_id)
    return render_template("mypage/edit.html", user_info=user_info, user_id=user_id)


@mypage_bp.route('/bankRegistration')
def bankRegistration():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT count(*) AS 登録数 FROM t_transfer t INNER JOIN m_account a ON t.account_id=a.id WHERE a.id=%s GROUP BY a.id", (user_id,))
    bank_count_row = cur.fetchone()
    cur.close(); con.close()
    bank_count = int(bank_count_row['登録数']) if bank_count_row else 0
    if bank_count >= 3:
        return render_template("mypage/mypage.html")
    return render_template("mypage/bankRegistration.html")


@mypage_bp.route('/bankComplete', methods=['POST'])
def bankComplete():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    bank_info = request.form
    if any(not v for v in bank_info.values()):
        return render_template('mypage/bankRegistration.html')
    id = session['user_id']
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM t_transfer WHERE account_id=%s AND branchCode=%s AND accountNumber=%s",
                (id, bank_info['branchCode'], bank_info['accountNumber']))
    if cur.fetchone():
        cur.close(); con.close()
        return render_template('mypage/bankRegistration.html')
    accountHolder = bank_info['famillyName'] + bank_info['firstName']
    cur.execute("INSERT INTO t_transfer (account_id,bankName,accountType,branchCode,accountNumber,accountHolder) VALUES(%s,%s,%s,%s,%s,%s)",
                (id, bank_info['name'], bank_info['accountType'], bank_info['branchCode'], bank_info['accountNumber'], accountHolder))
    con.commit()
    cur.close(); con.close()
    return render_template("mypage/bankComplete.html")


@mypage_bp.route('mypage/transferApplication')
def transferApplication():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    session['editmode'] = False
    bank_info, accountNumbers, count = getAccountInfo()
    return render_template("mypage/transferApplication.html", user_id=user_id,
                           bank_info=bank_info, accountNumbers=accountNumbers,
                           count=count, editmode=False)


@mypage_bp.route('/transferApplication')
def editActivate():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    session['editmode'] = not session.get('editmode', False)
    bank_info, accountNumbers, count = getAccountInfo()
    return render_template("mypage/transferApplication.html", user_id=user_id,
                           bank_info=bank_info, accountNumbers=accountNumbers,
                           count=count, editmode=session['editmode'])


@mypage_bp.route('/transferApplication/removeBank', methods=['POST'])
def removeBank():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    bank_id = request.form.get('bank_id')
    id = session['user_id']
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM t_transfer WHERE account_id=%s", (id,))
    target = cur.fetchall()
    target_id = target[int(bank_id)]['id']
    cur.execute("DELETE FROM t_transfer WHERE id=%s", (target_id,))
    con.commit()
    cur.close(); con.close()
    bank_info, accountNumbers, count = getAccountInfo()
    return render_template("mypage/transferApplication.html", user_id=user_id,
                           bank_info=bank_info, accountNumbers=accountNumbers, count=count,
                           editmode=session.get('editmode', False))


@mypage_bp.route('/personal_info')
def personal_info():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    return render_template('mypage/personal_info.html')


@mypage_bp.route('/privacyPolicy')
def privacyPolicy():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT content_detail FROM m_admin_contents WHERE id=2")
    result = cur.fetchone()
    cur.close(); con.close()
    return render_template("mypage/privacyPolicy.html", user_id=user_id, result=result)


@mypage_bp.route('/terms')
def terms():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT content_detail FROM m_admin_contents WHERE id=1")
    result = cur.fetchone()
    cur.close(); con.close()
    return render_template("mypage/terms.html", user_id=user_id, result=result)


@mypage_bp.route('/helpCenter')
def helpCenter():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    return render_template("mypage/helpCenter.html", user_id=user_id)


@mypage_bp.route('/inquiry')
def inquiry():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    return render_template("mypage/inquiry.html", user_id=user_id)


@mypage_bp.route('/likes')
def likes():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT p.id, p.name, p.purchasePrice, p.rentalPrice,
               p.purchaseFlg, p.rentalFlg, MIN(i.img) AS image_path
        FROM t_favorite f
        JOIN m_product p ON f.product_id = p.id
        LEFT JOIN m_productimg i ON p.id = i.product_id
        WHERE f.account_id = %s
        GROUP BY p.id, p.name, p.purchasePrice, p.rentalPrice, p.purchaseFlg, p.rentalFlg
    """, (user_id,))
    likes_list = cur.fetchall()
    cur.close(); con.close()
    return render_template("mypage/likes.html", user_id=user_id, likes_list=likes_list)


@mypage_bp.route('/follow')
def follow():
    if 'user_id' not in session:
        return redirect(url_for('login.login'))
    user_id = session.get('user_id')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("""
        SELECT a.id, a.username AS ユーザー名, a.profileImage AS アイコン,
               (SELECT AVG(e.score) FROM t_evaluation e WHERE e.recipient_id = a.id) AS 評価,
               (SELECT COUNT(e.score) FROM t_evaluation e WHERE e.recipient_id = a.id) AS 評価件数
        FROM m_account a
        WHERE a.id IN (SELECT target_id FROM t_connection WHERE type='フォロー' AND execution_id=%s)
    """, (user_id,))
    follow_list = cur.fetchall()
    cur.close(); con.close()
    for f in follow_list:
        f['評価'] = int(f['評価']) if f['評価'] else 0
        if not f['評価']:
            f['評価件数'] = 0
    return render_template("mypage/followList.html", follow_list=follow_list, user_id=user_id)
