-- Additional performance indexes and constraints

-- Add composite index for license queries
CREATE INDEX IF NOT EXISTS idx_licenses_product_status ON licenses(product_id, status);
CREATE INDEX IF NOT EXISTS idx_licenses_user_status ON licenses(user_id, status);

-- Add index for usage logs by action and time range
CREATE INDEX IF NOT EXISTS idx_logs_action_time ON usage_logs(action, timestamp);

-- Add check constraint for usage_count
ALTER TABLE licenses ADD CONSTRAINT chk_usage_count CHECK (usage_count >= 0);

-- Add unique constraint for license key per product (optional)
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_license_product 
-- ON licenses(product_id, key);

-- Add foreign key constraint for usage_logs (requires license key exists)
-- Note: SQLite doesn't support foreign keys in logs for performance reasons
-- But we can add a trigger to validate
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

-- Vacuum and analyze for better performance
VACUUM;
ANALYZE;