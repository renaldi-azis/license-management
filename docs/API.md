# 🎫 License Management API Documentation

---

## 🌐 Base URL

```
https://your-license-server.com/api
```

---

## 🔐 Authentication

<details>
<summary><strong>Login</strong> <code>POST /auth/login</code></summary>

**Request Body:**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": "admin"
}
```

**Response (401):**
```json
{
  "error": "Invalid credentials"
}
```
</details>

<details>
<summary><strong>Get Current User</strong> <code>GET /auth/me</code></summary>

**Headers:**  
`Authorization: Bearer <token>`

**Response (200):**
```json
{
  "user": "admin"
}
```
</details>

---

## 🛒 Products

<details>
<summary><strong>Create Product</strong> <code>POST /products</code> <em>(Admin only)</em></summary>

**Request Body:**
```json
{
  "name": "Pro Editor",
  "description": "Professional text editor",
  "max_devices": 2
}
```

**Response (201):**
```json
{
  "success": true,
  "product_id": 1
}
```
</details>

<details>
<summary><strong>List Products</strong> <code>GET /products?page=1</code></summary>

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 50)

**Response (200):**
```json
{
  "products": [
    {
      "id": 1,
      "name": "Pro Editor",
      "description": "Professional text editor",
      "max_devices": 2,
      "total_licenses": 15,
      "active_licenses": 12,
      "created_at": "2024-01-01T10:00:00"
    }
  ],
  "pagination": {
    "page": 1,
    "total": 1
  }
}
```
</details>

<details>
<summary><strong>Update Product</strong> <code>PUT /products/{product_id}</code> <em>(Admin only)</em></summary>

**Request Body:**
```json
{
  "name": "Updated Product Name",
  "max_devices": 3
}
```
</details>

<details>
<summary><strong>Get Product Stats</strong> <code>GET /products/{product_id}/stats</code> <em>(Admin only)</em></summary>

**Response (200):**
```json
{
  "product": {
    "id": 1,
    "name": "Pro Editor",
    "max_devices": 2
  },
  "license_stats": {
    "total_licenses": 15,
    "active_licenses": 12,
    "expired_licenses": 2,
    "revoked_licenses": 1,
    "avg_usage": 5.2,
    "max_usage": 25
  },
  "estimated_revenue": 120,
  "recent_validations": 45
}
```
</details>

---

## 🔑 Licenses

<details>
<summary><strong>Create License</strong> <code>POST /licenses</code> <em>(Admin only)</em></summary>

**Request Body:**
```json
{
  "product_id": 1,
  "user_id": "user123",
  "expires_days": 30
}
```

**Response (201):**
```json
{
  "license_key": "X7kP9mQ2vR4tY6uW8iO0pA2sD4fG6hJ8",
  "status": "created"
}
```
</details>

<details>
<summary><strong>List Licenses</strong> <code>GET /licenses?page=1&per_page=25</code></summary>

**Response (200):**
```json
{
  "licenses": [
    {
      "id": 1,
      "key_display": "X7kP9mQ2...",
      "product_name": "Pro Editor",
      "user_id": "user123",
      "status": "active",
      "created_at": "2024-01-01T10:00:00",
      "expires_at": "2024-01-31T10:00:00",
      "usage_count": 5
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 100
  }
}
```
</details>

<details>
<summary><strong>Revoke License</strong> <code>POST /licenses/{license_key}/revoke</code> <em>(Admin only)</em></summary>

**Response (200):**
```json
{
  "status": "revoked"
}
```
</details>

<details>
<summary><strong>Get License Statistics</strong> <code>GET /licenses/stats</code> <em>(Admin only)</em></summary>

**Response (200):**
```json
{
  "total_licenses": 150,
  "active_licenses": 120,
  "expired_licenses": 20,
  "revoked_licenses": 10,
  "avg_usage_per_license": 4.5,
  "max_usage": 35,
  "recent_validations": 250
}
```
</details>

---

## ✅ License Validation

<details>
<summary><strong>Validate License</strong> <code>GET /validate/{product_name}/{license_key}</code></summary>

**Path Parameters:**
- `product_name`: Name of the software product
- `license_key`: The license key to validate

**Response (200 - Valid):**
```json
{
  "valid": true,
  "license_id": 1,
  "product_name": "Pro Editor",
  "expires_at": "2024-01-31T10:00:00",
  "usage_count": 6,
  "max_devices": 2
}
```

**Response (400 - Invalid):**
```json
{
  "valid": false,
  "error": "License expired"
}
```
</details>

---

## 🚦 Rate Limiting

- **1000 requests per day per IP**
- **100 requests per hour per IP**
- **10 requests per minute for admin actions**

**Rate limited response (429):**
```json
{
  "error": "Too many requests. Please try again later."
}
```

---

## ⚠️ Error Responses

| Status | Example Response |
|--------|-----------------|
| 400 Bad Request | ```json { "error": "Missing required field: product_id" } ``` |
| 401 Unauthorized | ```json { "error": "Invalid or expired token" } ``` |
| 403 Forbidden | ```json { "error": "Admin access required" } ``` |
| 404 Not Found | ```json { "error": "Product not found" } ``` |
| 500 Internal Server Error | ```json { "error": "Internal server error" } ``` |
