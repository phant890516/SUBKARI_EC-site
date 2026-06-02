# ==========================================================
# Filename      : app/views/login.py
# Descriptions  : Login, registration, password reset routes
# ==========================================================
from flask import Blueprint, render_template, request, make_response, redirect, url_for, session
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import mysql.connector
import json
import os

login_bp = Blueprint('login', __name__, url_prefix='/login')

UPLOADS_RELATIVE_PATH = 'app/static/img/IdentityImg'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

ACCOUNT_SCHEMA = {
    'username':      (12,   True),
    'lastName':      (50,   True),
    'firstName':     (50,   True),
    'lastNameKana':  (50,   True),
    'firstNameKana': (50,   True),
    'birthday':      (None, True),
    'zip':           (7,    True),
    'pref':          (10,   True),
    'address1':      (20,   True),
    'address2':      (20,   True),
    'address3':      (40,   False),
    'tel':           (20,   True),
    'smoker':        (None, True),
}

@login_bp.route('/registration_complete', methods=['GET'])
def registration_complete():
    return render_template('login/registration_complete.html', message="ユーザー登録が完了しました。")

@login_bp.route('/login', methods=['GET'])
def login():
    return render_template('login/login.html', etbl={}, account={})

@login_bp.route('/login/auth', methods=['POST'])
def login_auth():
    account = request.form
    ecnt = sum(1 for v in account.values() if not v)
    if ecnt != 0:
        return render_template('login/login.html', account=account)
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM m_account WHERE mail = %s;", (account['mail'],))
    userExist = cur.fetchone()
    cur.close()
    con.close()
    if not userExist or userExist['password'] != account['password']:
        return render_template('login/login.html', account=account,
                               error_message="メールアドレスまたはパスワードが正しくありません。")
    session['user_id'] = userExist['id']
    return redirect(url_for('top.member_index'))

@login_bp.route('/login/logout', methods=['GET'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('top.guest_index'))

@login_bp.route("/register_user", methods=["GET"])
def show_register_user():
    account = {}
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT content_detail FROM m_admin_contents WHERE id=1")
    result = cur.fetchone()
    cur.close()
    con.close()
    if not result:
        result = {"content_detail": "利用規約の内容が登録されていません。"}
    return render_template("login/new_account.html", account=account, result=result)

@login_bp.route("/terms", methods=["GET"])
def show_terms():
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT content_detail FROM m_admin_contents WHERE id = 1")
    result = cur.fetchone()
    cur.close()
    con.close()
    return render_template("mypage/terms.html", result=result or {"content_detail": ""})

@login_bp.route('/privacy_policy', methods=['GET'])
def privacy_policy():
    return render_template('login/privacy.html')

@login_bp.route('/register_user/complete', methods=['POST'])
def register_user_complete():
    account = request.form
    if account['password'] != account['password_confirm']:
        return render_template('login/new_account.html',
                               error="パスワードが一致しません。", account=account)
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM m_account WHERE mail = %s;", (account['mail'],))
    userExist = cur.fetchone()
    cur.close()
    con.close()
    if userExist:
        return render_template('login/new_account.html',
                               error_same="このメールアドレスはすでに登録されています。", account=account)
    session['registration_data'] = dict(account)
    return redirect(url_for('login.show_register_form'))

@login_bp.route("/register_user/form", methods=["GET"])
def show_register_form():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    return render_template('login/register_form.html', errors={}, form_data={})

@login_bp.route("register_user/form_complete", methods=["POST"])
def registration_form_complete():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    form_data = request.form
    errors = {}
    for name, (max_length, is_required) in ACCOUNT_SCHEMA.items():
        value = form_data.get(name)
        if is_required and not value:
            errors[name] = "この項目は必須です。"
            continue
        if value and max_length and len(value) > max_length:
            errors[name] = f"{max_length}文字以内で入力してください。"
    tel_value = form_data.get('tel')
    if tel_value and not tel_value.isdigit():
        errors['tel'] = "電話番号はハイフンなしの半角数字で入力してください。"
    if errors:
        return render_template('login/register_form.html', errors=errors, form_data=form_data)
    existing_data = session.get('registration_data', {})
    existing_data.update(dict(form_data))
    session['registration_data'] = existing_data
    return redirect(url_for('login.show_phone_verification'))

@login_bp.route("/phone_verification", methods=["GET"])
def show_phone_verification():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    return render_template('login/Phone_verification.html')

@login_bp.route("register_user/phone_auth", methods=["POST"])
def phone_auth():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    return render_template('login/identity_verification.html')

@login_bp.route("register_user/phone_auth_resend", methods=["POST"])
def phone_auth_resend():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    return render_template('login/Phone_verification.html')

@login_bp.route("register_user/verification", methods=["POST"])
def verification():
    if 'registration_data' not in session:
        return redirect(url_for('login.show_register_user'))
    front_image = request.files.get('front_image')
    back_image  = request.files.get('back_image')
    if not front_image or front_image.filename == '':
        return render_template('login/identity_verification.html',
                               message="本人確認書類の表面画像をアップロードしてください。")
    all_data = session['registration_data']
    account_data = (
        all_data.get('mail'), all_data.get('password'), all_data.get('username'),
        all_data.get('lastName'), all_data.get('firstName'),
        all_data.get('lastNameKana'), all_data.get('firstNameKana'),
        all_data.get('birthday'), all_data.get('tel'),
        all_data.get('smoker') == 'yes',
    )
    address_data = (
        all_data.get('zip'), all_data.get('pref'),
        all_data.get('address1'), all_data.get('address2'), all_data.get('address3'),
    )
    con = connect_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM m_account WHERE mail = %s;", (all_data['mail'],))
    if cur.fetchone():
        cur.close(); con.close()
        return render_template('login/new_account.html', error={}, error_same={})
    sql_account = """
        INSERT INTO m_account
        (mail, password, username, lastName, firstName, lastNameKana, firstNameKana,
         birthday, tel, smoker, profileImage, status,
         identifyfrontImg, identifybackImg)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'default_profile.jpg', '未確認', '', '')
    """
    cur.execute(sql_account, account_data)
    con.commit()
    new_account_id = cur.lastrowid
    cur.execute(
        "INSERT INTO m_address (account_id, zip, pref, address1, address2, address3) VALUES (%s, %s, %s, %s, %s, %s)",
        (new_account_id,) + address_data
    )
    con.commit()
    upload_path = UPLOADS_RELATIVE_PATH
    os.makedirs(upload_path, exist_ok=True)
    for field, col in [('front_image', 'identifyfrontImg'), ('back_image', 'identifybackImg')]:
        f = request.files.get(field)
        if f and f.filename and allowed_file(f.filename):
            fname = secure_filename(f.filename)
            fname = datetime.now().strftime('%Y%m%d%H%M%S_') + fname
            f.save(os.path.join(upload_path, fname))
            cur.execute(f"UPDATE m_account SET {col} = %s WHERE id = %s", (fname, new_account_id))
            con.commit()
    cur.close(); con.close()
    session.pop('registration_data', None)
    return render_template('login/registration_complete.html')

@login_bp.route('/password-reset', methods=['GET'])
def password_reset():
    return render_template('login/forgot_password.html', error=None, success=None, message=None)

@login_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    email_address = request.form.get('email')
    con = connect_db()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM m_account WHERE mail = %s;", (email_address,))
    userExist = cur.fetchone()
    cur.close(); con.close()
    if not userExist:
        return render_template('login/forgot_password.html',
                               message="このメールアドレスは登録されていません")
    session['reset_email'] = email_address
    return render_template('login/forgot_password.html',
                           success="パスワードリセットのメールを送信しました。")

@login_bp.route('/forgot_email', methods=['GET'])
def forgot_email():
    return render_template('login/forgot_email.html')
