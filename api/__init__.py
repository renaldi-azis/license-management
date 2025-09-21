from .auth import bp as auth_bp
from .licenses import bp as licenses_bp
from .products import bp as products_bp

__all__ = ['auth_bp', 'licenses_bp', 'products_bp']