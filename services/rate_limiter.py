import redis
from flask import current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta

# Redis client
redis_client = redis.Redis.from_url(current_app.config['REDIS_URL'], decode_responses=True)

def init_limiter(app):
    """Initialize Flask-Limiter with Redis backend."""
    Limiter(
        app,
        key_func=get_remote_address,
        default_limits=["1000 per day", "100 per hour"],
        storage_uri=current_app.config['REDIS_URL']
    )

def suspicious_activity_check(ip_address):
    """Check if IP shows suspicious activity patterns."""
    # Check spam score
    spam_score = redis_client.get(f"spam_score:{ip_address}")
    if spam_score and int(spam_score) > 100:
        return True
    
    # Check rapid requests (more than 50 in 5 minutes)
    recent_requests = redis_client.zcount(
        f"requests:{ip_address}",
        int((current_app.now() - timedelta(minutes=5)).timestamp()),
        int(current_app.now().timestamp())
    )
    
    if recent_requests > 50:
        redis_client.incr(f"spam_score:{ip_address}")
        redis_client.expire(f"spam_score:{ip_address}", 86400)  # 24 hours
        return True
    
    # Track current request
    redis_client.zadd(f"requests:{ip_address}", {str(current_app.now().timestamp()): 1})
    redis_client.expire(f"requests:{ip_address}", 3600)  # 1 hour
    
    return False

def record_suspicious_activity(ip_address, reason="unknown"):
    """Record suspicious activity for monitoring."""
    redis_client.incr(f"spam_score:{ip_address}")
    redis_client.expire(f"spam_score:{ip_address}", 86400)
    
    # Log the incident
    timestamp = current_app.now().timestamp()
    redis_client.lpush(f"suspicious_logs:{ip_address}", f"{timestamp}:{reason}")
    redis_client.ltrim(f"suspicious_logs:{ip_address}", 0, 99)  # Keep last 100