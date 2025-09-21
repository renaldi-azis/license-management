from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from api import auth, licenses, products
from models.database import init_db
from services.rate_limiter import init_limiter
from services.security import init_recaptcha

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    JWTManager(app)
    init_db()
    init_limiter(app)
    init_recaptcha(app)
    
    # Register blueprints
    app.register_blueprint(auth.bp, url_prefix='/api')
    app.register_blueprint(licenses.bp, url_prefix='/api')
    app.register_blueprint(products.bp, url_prefix='/api')
    
    # Routes
    @app.route('/')
    def index():
        return render_template('base.html')
    
    @app.route('/admin')
    def admin():
        return render_template('admin.html')
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)