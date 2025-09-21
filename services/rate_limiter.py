import redis
from flask import current_app, has_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from contextlib import contextmanager
import time
import json

# Global Redis client (initialized after app creation)
redis_client = None

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri=None  # Will set later
)

def init_limiter(app):
    """Initialize Flask-Limiter with Redis backend."""
    global redis_client
    
    # Initialize Redis client
    redis_client = redis.from_url(app.config['REDIS_URL'], decode_responses=True)
    
    # Test Redis connection
    try:
        redis_client.ping()
        app.logger.info("Redis connection established for rate limiting")
    except Exception as e:
        app.logger.warning(f"Redis connection failed: {e}. Rate limiting will be limited.")
    
    limiter.storage_uri = app.config['REDIS_URL']
    limiter.init_app(app)

def get_current_time():
    """Get current timestamp compatible with Flask context."""
    if has_request_context():
        return current_app.now() if hasattr(current_app, 'now') else time.time()
    return time.time()

@contextmanager
def app_context():
    """Provide application context when needed."""
    if has_request_context():
        yield
    else:
        with current_app.app_context():
            yield

def suspicious_activity_check(ip_address):
    """Check if IP shows suspicious activity patterns."""
    if not redis_client:
        return False
    
    try:
        with app_context():
            # Check spam score
            spam_score = redis_client.get(f"spam_score:{ip_address}")
            if spam_score and int(spam_score) > 100:
                return True
        
            # Check rapid requests (more than 50 in 5 minutes)
            five_min_ago = get_current_time() - 300  # 5 minutes ago
            recent_requests = redis_client.zcount(
                f"requests:{ip_address}",
                int(five_min_ago),
                int(get_current_time())
            )
        
            if recent_requests > 50:
                redis_client.incr(f"spam_score:{ip_address}")
                redis_client.expire(f"spam_score:{ip_address}", 86400)  # 24 hours
                return True
        
            # Track current request
            timestamp = get_current_time()
            redis_client.zadd(f"requests:{ip_address}", {str(timestamp): timestamp})
            redis_client.expire(f"requests:{ip_address}", 3600)  # 1 hour
        
        return False
    except Exception as e:
        # Log error but don't fail the request
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Rate limiting error for {ip_address}: {e}")
        return False

def record_suspicious_activity(ip_address, reason="unknown", score=0):
    """Record suspicious activity for monitoring."""
    if not redis_client:
        return
    
    try:
        with app_context():
            redis_client.incr(f"spam_score:{ip_address}")
            redis_client.expire(f"spam_score:{ip_address}", 86400)
        
            # Log the incident
            timestamp = get_current_time()
            redis_client.lpush(f"suspicious_logs:{ip_address}", f"{timestamp}:{reason}:{score}")
            redis_client.ltrim(f"suspicious_logs:{ip_address}", 0, 99)  # Keep last 100
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to record suspicious activity: {e}")

def get_ip_stats(ip_address):
    """Get detailed statistics for an IP address."""
    if not redis_client:
        return {}
    
    try:
        with app_context():
            stats = {
                "spam_score": int(redis_client.get(f"spam_score:{ip_address}") or 0),
                "recent_requests": redis_client.zcard(f"requests:{ip_address}"),
                "suspicious_events": redis_client.llen(f"suspicious_logs:{ip_address}")
            }
            
            # Get recent suspicious events
            recent_events = redis_client.lrange(f"suspicious_logs:{ip_address}", 0, 4)
            stats["recent_suspicious"] = [event.decode() for event in recent_events]
            
            return stats
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to get IP stats: {e}")
        return {}

def block_ip(ip_address, duration_hours=24):
    """Block an IP address for specified duration."""
    if not redis_client:
        return
    
    try:
        with app_context():
            block_duration = int(timedelta(hours=duration_hours).total_seconds())
            redis_client.setex(f"blocked:{ip_address}", block_duration, "1")
            
            # Log the block
            record_suspicious_activity(ip_address, "manual_block", 1000)
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to block IP {ip_address}: {e}")

def unblock_ip(ip_address):
    """Remove IP from block list."""
    if not redis_client:
        return
    
    try:
        with app_context():
            redis_client.delete(f"blocked:{ip_address}")
            if current_app and hasattr(current_app, 'logger'):
                current_app.logger.info(f"IP unblocked: {ip_address}")
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to unblock IP {ip_address}: {e}")

def is_ip_blocked(ip_address):
    """Check if IP is currently blocked."""
    if not redis_client:
        return False
    
    try:
        return redis_client.get(f"blocked:{ip_address}") is not None
    except:
        return False

# Decorator for rate-limited routes
def rate_limited(limit="100/hour"):
    """Decorator to apply rate limiting to routes."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_request_context():
                return f(*args, **kwargs)
            
            ip = get_remote_address()
            
            # Check if IP is blocked
            if is_ip_blocked(ip):
                return current_app.response_class(
                    json.dumps({
                        "error": "IP address blocked due to previous abuse",
                        "retry_after": 3600
                    }),
                    status=403,
                    mimetype='application/json'
                )
            
            # Check suspicious activity
            if suspicious_activity_check(ip):
                # Record as suspicious
                record_suspicious_activity(ip, "high_request_rate", 50)
                
                return current_app.response_class(
                    json.dumps({
                        "error": "Too many requests. Please try again later.",
                        "retry_after": 300
                    }),
                    status=429,
                    mimetype='application/json'
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Admin-only rate limiting
def admin_rate_limited(limit="10/minute"):
    """Enhanced rate limiting for admin routes."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        @rate_limited("50/hour")  # Base limit
        def decorated_function(*args, **kwargs):
            if not has_request_context():
                return f(*args, **kwargs)
            
            from flask_jwt_extended import get_jwt_identity
            
            try:
                current_user = get_jwt_identity()
                if current_user != 'admin':
                    return current_app.response_class(
                        json.dumps({"error": "Admin access required"}),
                        status=403,
                        mimetype='application/json'
                    )
            except:
                return current_app.response_class(
                    json.dumps({"error": "Authentication required"}),
                    status=401,
                    mimetype='application/json'
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator