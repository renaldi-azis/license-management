# Security and Rate Limiting Overview

This document describes the security-related functions and their usages from `services/rate_limiter.py`.

---

## Function Usages

### `init_limiter(app)`
**Usage:**  
Initializes the Flask-Limiter extension with a Redis backend for rate limiting.  
**When/Where:**  
Called during app startup to set up global rate limiting and connect to Redis.

---

### `get_current_time()`
**Usage:**  
Returns the current timestamp, using Flask's context if available.  
**When/Where:**  
Used internally for accurate request timing and logging.

---

### `app_context()`
**Usage:**  
Context manager to ensure code runs within a Flask application context.  
**When/Where:**  
Used internally by functions that interact with Flask or Redis, especially outside request contexts.

---

### `suspicious_activity_check(ip_address)`
**Usage:**  
Checks if an IP address is exhibiting suspicious behavior (e.g., high request rate or high spam score).  
**When/Where:**  
Called before processing requests to detect and mitigate abuse or spam.

---

### `record_suspicious_activity(ip_address, reason="unknown", score=0)`
**Usage:**  
Records suspicious activity for an IP address, increments its spam score, and logs the event in Redis.  
**When/Where:**  
Called when suspicious activity is detected, for monitoring and future blocking.

---

### `get_ip_stats(ip_address)`
**Usage:**  
Retrieves statistics for a given IP address, including spam score, recent requests, and suspicious events.  
**When/Where:**  
Used for monitoring, admin dashboards, or diagnostics.

---

### `block_ip(ip_address, duration_hours=24)`
**Usage:**  
Blocks an IP address for a specified duration (default: 24 hours) by setting a Redis key.  
**When/Where:**  
Can be called manually by admins or automatically after repeated abuse.

---

### `unblock_ip(ip_address)`
**Usage:**  
Removes an IP address from the block list in Redis.  
**When/Where:**  
Used by admins to restore access for previously blocked IPs.

---

### `is_ip_blocked(ip_address)`
**Usage:**  
Checks if an IP address is currently blocked.  
**When/Where:**  
Called before processing requests to enforce blocks.

---

### `rate_limited(limit="100/hour")`
**Usage:**  
Decorator to apply custom rate limiting and abuse checks to Flask routes.  
- Checks if the IP is blocked.
- Checks for suspicious activity.
- Returns appropriate error responses if limits are exceeded or IP is blocked.
**When/Where:**  
Applied to Flask route handlers to enforce per-route rate limits and abuse protection.

---

## Security Notes

- All rate limiting and abuse detection is backed by Redis for performance and persistence.
- Suspicious activity is tracked and can lead to temporary or permanent IP blocking.
- Admins can monitor and manage IP statistics and blocks using the provided functions.
- The decorator ensures that abusive clients are throttled or blocked before reaching sensitive