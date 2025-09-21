"""Test configuration."""
import pytest
from app import create_app
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    REDIS_URL = 'redis://localhost:6379/1'  # Different DB for tests
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key'


@pytest.fixture
def app():
    app = create_app()
    app.config.from_object(TestConfig)
    
    with app.app_context():
        from models.database import init_db
        init_db()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()