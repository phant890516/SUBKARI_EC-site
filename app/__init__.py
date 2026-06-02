# ==========================================================
# Filename      : app/__init__.py
# Descriptions  : Application Factory
# ==========================================================
from flask import Flask, render_template
from config import Config
import os

pem_env = os.environ.get('AIVEN_CA_PEM')
if pem_env:
    with open('ca.pem', 'w') as f:
        f.write(pem_env)
else:
    print('⚠️ AIVEN_CA_PEM not found in environment variables!')


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    from .views import top, login, products, seller, dashboard, mypage, deal, userprf, brand_serach

    app.register_blueprint(top.top_bp)
    app.register_blueprint(login.login_bp)
    app.register_blueprint(products.products_bp)
    app.register_blueprint(seller.seller_bp)
    app.register_blueprint(dashboard.dashboard_bp)
    app.register_blueprint(mypage.mypage_bp)
    app.register_blueprint(deal.deal_bp)
    app.register_blueprint(userprf.userprf_bp)
    app.register_blueprint(brand_serach.brand_serach_bp)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('error.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('error.html'), 500

    return app
