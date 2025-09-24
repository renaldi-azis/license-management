# License Management Server

## Overview

This project is a secure license management server with a RESTful API, designed for easy integration with Python applications. It supports license creation, validation, revocation, usage logging, and anti-abuse mechanisms. The server can manage licenses for multiple software products and includes a web-based admin dashboard.

---

## Features

- **API Endpoints:**
  - Create, revoke, and validate license keys
  - Manage license status: active, expired, blocked
  - Log usage history and requests
  - Search licenses by account name or license value

- **Integration:**
  - Simple Python requests for license verification
  - Supports multiple software products

- **Security:**
  - Resistant to cracking and bypassing
  - Rate limiting and token-based authentication to prevent spam and abuse

- **Admin Dashboard:**
  - Manage licenses and accounts via web panel
  - View license details and usage logs
  - Permanently delete licenses
  - Export license data to Excel

---

## Special Notes

- **Default Accounts:**  
  Registration is disabled. Five default accounts are created:
    - `richtoolsmmo01` — `RichTools2025!`
    - `richtoolsmmo_backup` — `RichBackup21#`
    - `huytoolsmmo01` — `HuyTools2025!`
    - `huytoolsmmo_admin` — `HuyAdmin#77`
    - `richtoolsmmo.huy` — `RtHuyHome99`

- **License Creation:**  
  When creating a license, you must enter:
    - `UserID`
    - `Credit Number` (optional; if not entered, API returns `None`)
    - `Machine Code`

- **License Actions:**  
  - Copy and details buttons work in the dashboard; details are shown for selected licenses.
  - Search box allows searching by account name or license value.
  - Delete button allows permanent removal of licenses.
  - Backup button exports license data to Excel.

---

## Anti-Spam & Quota

- Rate limiting and authentication prevent abuse and spam, avoiding issues like Google API quota errors.

---

## Running Steps

1. **Initialize Database:**
   ```sh
   python -c "from models.database import drop_users_table; drop_users_table()"
   python -c "from models.database import insert_default_users; insert_default_users()"
   python -c "from models.database import init_db; init_db()"
   ```

2. **Start Server:**
   ```sh
   flask run --host=0.0.0.0 --port=5000
   ```

---

## Contact

For questions or support, contact:  
Phuong