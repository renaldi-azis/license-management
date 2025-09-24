-- Initial database schema for license management system

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    max_devices INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Licenses table
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    product_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'revoked')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    credit_number TEXT DEFAULT 'None',
    machine_code TEXT DEFAULT 'None',
    device_id TEXT,
    last_used_at TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
);

-- Usage logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    user_agent TEXT,
    response_status TEXT,
    duration_ms INTEGER,
    error_message TEXT
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    credit_number TEXT DEFAULT 'Not Provided',
    machine_code TEXT DEFAULT 'Not Provided',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(key);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
CREATE INDEX IF NOT EXISTS idx_licenses_product ON licenses(product_id);
CREATE INDEX IF NOT EXISTS idx_licenses_user ON licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_licenses_expires ON licenses(expires_at);
CREATE INDEX IF NOT EXISTS idx_logs_license ON usage_logs(license_key);
CREATE INDEX IF NOT EXISTS idx_logs_ip ON usage_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON usage_logs(timestamp);

-- Trigger to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_products_updated_at
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger to update last_used_at on license validation
CREATE TRIGGER IF NOT EXISTS update_license_last_used
AFTER UPDATE ON licenses
FOR EACH ROW
WHEN NEW.usage_count > OLD.usage_count
BEGIN
    UPDATE licenses SET last_used_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Sample data (uncomment to populate initial data)
-- INSERT OR IGNORE INTO products (name, description, max_devices) VALUES
-- ('Pro Editor', 'Professional text editor', 2),
-- ('Mobile App', 'Mobile productivity app', 3),
-- ('Desktop Suite', 'Complete desktop suite', 1);