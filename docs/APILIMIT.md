# API Rate Limits Overview

This document categorizes all API endpoints in the License Management project by their rate limiting level.

---

## 1. **Strict Rate Limit (10 per minute)**

| Endpoint                                      | Method(s) | Description                        |
|------------------------------------------------|-----------|------------------------------------|
| `/api/auth/login`                              | POST      | User login (prevents brute-force)  |
| `/api/validate/<product>/<license_key>`        | GET       | License validation                 |

---

## 2. **Moderate Rate Limit (30 per minute)**

| Endpoint                                      | Method(s) | Description                        |
|------------------------------------------------|-----------|------------------------------------|
| `/api/auth/register`                           | POST      | User registration                  |

---

## 3. **Default Rate Limit (60 per minute, 3600 per hour)**

All other API endpoints not explicitly listed above are protected by the default global rate limit.

| Endpoint                                      | Method(s) | Description                        |
|------------------------------------------------|-----------|------------------------------------|
| `/api/products`                               | GET, POST | Product listing/creation           |
| `/api/products/<product_id>`                  | PUT       | Product update                     |
| `/api/products/<product_id>/stats`            | GET       | Product statistics                 |
| `/api/licenses`                               | GET, POST | License listing/creation           |
| `/api/licenses/<license_key>/revoke`          | POST      | License revocation                 |
| `/api/licenses/stats`                         | GET       | License statistics                 |
| `/api/licenses/test/data`                     | GET       | Test license data (for testing)    |
| `/api/products/all`                           | GET       | List all products (for testing)    |
| ...                                           | ...       | Other general endpoints            |

---

## 4. **Admin/Privileged Endpoints**

Admin endpoints (such as product and license management) may have custom limits (often 10 per minute) to prevent abuse.

| Endpoint                                      | Method(s) | Description                        | Limit         |
|------------------------------------------------|-----------|------------------------------------|---------------|
| `/api/products` (admin actions)               | POST      | Create product                     | 10 per minute |
| `/api/licenses` (admin actions)               | POST      | Create license                     | 10 per minute |

---

## IP Blocking

- **How it works:**  
  Every API request is checked for suspicious activity using `suspicious_activity_check(ip)`.  
  If an IP exceeds abuse thresholds (e.g., too many failed attempts, high spam score), it is automatically blocked (default: 24 hours).
- **Blocked IPs:**  
  Blocked IPs receive a `429 Too Many Requests` response and cannot access any API endpoints until unblocked.
- **Manual Unblocking:**  
  Admins can unblock IPs using the `unblock_ip(ip_address)` function.
- **Monitoring:**  
  IP statistics and block status can be monitored for security auditing.

---

## Example Blocked Response

```json
{
  "valid": false,
  "error": "Too many requests from this IP. Please try again later.",
  "error_code": "RATE_LIMITED"
}
```

---

**Note:**  
All rate limits and blocking durations can be configured in the application settings and rate limiter