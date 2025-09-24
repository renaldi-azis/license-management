-- Additional performance indexes and constraints

-- Add composite index for license queries
CREATE INDEX IF NOT EXISTS idx_licenses_product_status ON licenses(product_id, status);
CREATE INDEX IF NOT EXISTS idx_licenses_user_status ON licenses(user_id, status);

-- Add index for usage logs by action and time range
CREATE INDEX IF NOT EXISTS idx_logs_action_time ON usage_logs(action, timestamp);

-- Add check constraint for usage_count (if not already present)
-- SQLite does not support ALTER TABLE ADD CONSTRAINT for CHECK after creation,
-- so this is only for documentation or for other RDBMS.
-- If you need to enforce, recreate the table with the constraint.
-- ALTER TABLE licenses ADD CONSTRAINT chk_usage_count CHECK (usage_count >= 0);

-- Add unique constraint for license key per product (optional)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_license_product 
-- ON licenses(product_id, key);

-- Add foreign key constraint for usage_logs (requires license key exists)
-- Note: SQLite doesn't enforce foreign keys on arbitrary columns,
-- but we can add a trigger to validate
DROP TRIGGER IF EXISTS validate_log_license;
CREATE TRIGGER IF NOT EXISTS validate_log_license
BEFORE INSERT ON usage_logs
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'License key not found') 
    WHERE NEW.license_key NOT IN (SELECT key FROM licenses);
END;

-- Add partial index for active licenses only
CREATE INDEX IF NOT EXISTS idx_active_licenses_product 
ON licenses(product_id) WHERE status = 'active';

-- Add index for IP-based spam detection
CREATE INDEX IF NOT EXISTS idx_logs_ip_action 
ON usage_logs(ip_address, action) 
WHERE action LIKE '%validation%' OR action LIKE '%error%';

-- Add index for credit_number and machine_code in licenses and users for fast lookup
CREATE INDEX IF NOT EXISTS idx_licenses_credit_number ON licenses(credit_number);
CREATE INDEX IF NOT EXISTS idx_licenses_machine_code ON licenses(machine_code);
CREATE INDEX IF NOT EXISTS idx_users_credit_number ON users(credit_number);
CREATE INDEX IF NOT EXISTS idx_users_machine_code ON users(machine_code);

-- Vacuum and analyze for better performance
VACUUM;
ANALYZE;