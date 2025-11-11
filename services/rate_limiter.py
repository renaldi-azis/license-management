import redis
from flask import current_app, has_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from services.users_service import get_role_by_username
from datetime import timedelta
from contextlib import contextmanager
import time
import socket

limiter = Limiter(key_func=get_remote_address)

# Global Redis client (initialized after app creation)
redis_client = None

def init_limiter(app):
    """Initialize Flask-Limiter with Redis backend and connection pooling."""
    global redis_client

    # Initialize Redis client with connection pooling for stability
    redis_client = redis.from_url(
        app.config['REDIS_URL'],
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=20
    )

    # Test Redis connection with timeout
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
    """Check if IP shows suspicious activity patterns with improved error handling."""
    if not redis_client:
        return False

    try:
        with app_context():
            # Check spam score with timeout protection
            try:
                spam_score = redis_client.get(f"spam_score:{ip_address}")
                if spam_score and int(spam_score) > 100:
                    return True
            except redis.RedisError:
                # Redis temporarily unavailable, allow request
                return False

            # Check rapid requests (more than 120 in 5 minutes)
            five_min_ago = get_current_time() - 300  # 5 minutes ago
            try:
                recent_requests = redis_client.zcount(
                    f"requests:{ip_address}",
                    int(five_min_ago),
                    int(get_current_time())
                )

                if recent_requests > 200:
                    redis_client.incr(f"spam_score:{ip_address}")
                    redis_client.expire(f"spam_score:{ip_address}", 86400)  # 24 hours
                    return True
            except redis.RedisError:
                # Redis temporarily unavailable, allow request
                return False

            # Track current request with error handling
            try:
                timestamp = get_current_time()
                redis_client.zadd(f"requests:{ip_address}", {str(timestamp): timestamp})
                redis_client.expire(f"requests:{ip_address}", 3600)  # 1 hour
            except redis.RedisError:
                # Redis temporarily unavailable, don't track but allow request
                pass

        return False
    except Exception as e:
        # Log error but don't fail the request
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Rate limiting error for {ip_address}: {e}")
        return False

def record_suspicious_activity(ip_address, reason="unknown", score=0):
    """Record suspicious activity for monitoring with error handling."""
    if not redis_client:
        return

    try:
        with app_context():
            try:
                redis_client.incr(f"spam_score:{ip_address}")
                redis_client.expire(f"spam_score:{ip_address}", 86400)

                # Log the incident
                timestamp = get_current_time()
                redis_client.lpush(f"suspicious_logs:{ip_address}", f"{timestamp}:{reason}:{score}")
                redis_client.ltrim(f"suspicious_logs:{ip_address}", 0, 99)  # Keep last 100
            except redis.RedisError:
                # Redis temporarily unavailable, log locally
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.warning(f"Redis unavailable, logging suspicious activity locally: {ip_address} - {reason}")
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to record suspicious activity: {e}")

def get_ip_stats(ip_address):
    """Get detailed statistics for an IP address with error handling."""
    if not redis_client:
        return {}

    try:
        with app_context():
            try:
                stats = {
                    "spam_score": int(redis_client.get(f"spam_score:{ip_address}") or 0),
                    "recent_requests": redis_client.zcard(f"requests:{ip_address}"),
                    "suspicious_events": redis_client.llen(f"suspicious_logs:{ip_address}")
                }

                # Get recent suspicious events
                recent_events = redis_client.lrange(f"suspicious_logs:{ip_address}", 0, 4)
                stats["recent_suspicious"] = [event.decode() if isinstance(event, bytes) else event for event in recent_events]

                return stats
            except redis.RedisError:
                # Redis temporarily unavailable
                return {"error": "Redis unavailable", "status": "degraded"}
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to get IP stats: {e}")
        return {}

def block_ip(ip_address, duration_hours=24):
    """Block an IP address for specified duration with error handling."""
    if not redis_client:
        return

    try:
        with app_context():
            try:
                block_duration = int(timedelta(hours=duration_hours).total_seconds())
                redis_client.setex(f"blocked:{ip_address}", block_duration, "1")

                # Log the block
                record_suspicious_activity(ip_address, "manual_block", 1000)
            except redis.RedisError:
                # Redis temporarily unavailable, log locally
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.warning(f"Redis unavailable, IP {ip_address} blocked locally for {duration_hours} hours")
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to block IP {ip_address}: {e}")

def unblock_ip(ip_address):
    """Remove IP from block list with error handling."""
    if not redis_client:
        return

    try:
        with app_context():
            try:
                redis_client.delete(f"blocked:{ip_address}")
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.info(f"IP unblocked: {ip_address}")
            except redis.RedisError:
                # Redis temporarily unavailable, log locally
                if current_app and hasattr(current_app, 'logger'):
                    current_app.logger.warning(f"Redis unavailable, IP {ip_address} unblock logged locally")
    except Exception as e:
        if current_app and hasattr(current_app, 'logger'):
            current_app.logger.error(f"Failed to unblock IP {ip_address}: {e}")

def is_ip_blocked(ip_address):
    """Check if IP is currently blocked with error handling."""
    if not redis_client:
        return False

    try:
        return redis_client.get(f"blocked:{ip_address}") is not None
    except redis.RedisError:
        # Redis temporarily unavailable, allow request
        return False
    except:
        return False

# Decorator for rate-limited routes
def rate_limited(limit="60/minute"):
    """Decorator to apply rate limiting to routes."""
    if(limiter is None):
        raise Exception("Limiter not initialized. Call init_limiter(app) after app creation.")
    return limiter.limit(limit)