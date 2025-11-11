import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-me'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///licenses.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database connection pooling for stability
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,  # Recycle connections every hour
        'pool_pre_ping': True,  # Test connections before use
        'connect_args': {
            'connect_timeout': 10,  # Connection timeout
        }
    }

    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL') or "redis://localhost:6379/0"
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_COOKIE_CSRF_PROTECT = False  # For testing; enable for production
    JWT_COOKIE_SECURE = False
    RECAPTCHA_SITE_KEY = "hobit-321"
    RECAPTCHA_SECRET_KEY = "hobit-321"

    # Server timeout configurations for stability
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes in seconds
    SEND_FILE_MAX_AGE_DEFAULT = 300  # 5 minutes cache

    # Connection pooling settings
    REQUEST_TIMEOUT = 30  # Default request timeout in seconds
    CONNECTION_POOL_SIZE = 100
    MAX_KEEPALIVE_CONNECTIONS = 20