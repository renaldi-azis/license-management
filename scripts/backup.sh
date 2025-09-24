#!/bin/bash

# License Server Backup Script

set -e

# Configuration
BACKUP_DIR="/backups/license-server"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/license-server"
LOG_FILE="/var/log/license-backup.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${YELLOW}INFO: $1${NC}" | tee -a "$LOG_FILE"
}

# Create backup directory
info "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR" || error "Failed to create backup directory"

# Stop application for consistent backup
info "Stopping license server..."
if systemctl is-active --quiet license-server; then
    systemctl stop license-server || error "Failed to stop license server"
else
    info "License server is not running"
fi

# Backup SQLite database(s)
DB_FILE="$APP_DIR/data/licenses.db"
if [ -f "$DB_FILE" ]; then
    info "Backing up database..."
    cp "$DB_FILE" "$BACKUP_DIR/licenses_$DATE.db" || error "Database backup failed"
    # Verify backup
    if sqlite3 "$BACKUP_DIR/licenses_$DATE.db" "PRAGMA integrity_check;" | grep -q 'ok'; then
        success "Database backup completed: $(du -h "$BACKUP_DIR/licenses_$DATE.db" | cut -f1)"
    else
        error "Database backup integrity check failed"
    fi
else
    info "No SQLite database found, skipping database backup"
fi

# Backup Redis data (if using Redis)
if command -v redis-cli >/dev/null 2>&1 && pgrep redis-server >/dev/null 2>&1; then
    info "Backing up Redis data..."
    redis-cli --rdb "$BACKUP_DIR/redis_$DATE.rdb" 2>/dev/null || {
        info "Redis backup failed or not needed"
    }
else
    info "Redis is not running or not installed, skipping Redis backup"
fi

# Backup configuration (exclude secrets and unnecessary files)
info "Backing up configuration..."
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
    --exclude=".env" \
    --exclude="venv" \
    --exclude="data" \
    --exclude="logs" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    -C "$APP_DIR" . 2>/dev/null || {
    info "Configuration backup skipped (no changes)"
}

# Backup logs (last 7 days)
LOGS_DIR="$APP_DIR/logs"
if [ -d "$LOGS_DIR" ]; then
    info "Backing up recent logs..."
    find "$LOGS_DIR" -name "*.log" -mtime -7 -print0 | xargs -0 tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" 2>/dev/null || {
        info "No recent logs to backup"
    }
else
    info "Logs directory not found, skipping logs backup"
fi

# Start application
info "Starting license server..."
systemctl start license-server 2>/dev/null || {
    info "Application already running or manual start required"
}

# Cleanup old backups (keep 7 days)
info "Cleaning up old backups..."
find "$BACKUP_DIR" -name "licenses_*.db" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "redis_*.rdb" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "logs_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "manifest_*.txt" -mtime +7 -delete 2>/dev/null || true

# Create manifest
info "Creating backup manifest..."
cat > "$BACKUP_DIR/manifest_$DATE.txt" << EOF
License Server Backup Manifest
Generated: $(date)
Hostname: $(hostname)
Backup Directory: $BACKUP_DIR

Files included:
$(ls -lh "$BACKUP_DIR"/*_$DATE.* 2>/dev/null | grep -v manifest || echo "No files in this backup")

Database size: $(du -sh "$DB_FILE" 2>/dev/null || echo "N/A")
System: $(uname -a)
EOF

# Summary
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
success "Backup completed successfully! Total size: $BACKUP_SIZE"
success "Files backed up:"
ls -lh "$BACKUP_DIR"/*_$DATE.* 2>/dev/null | grep -v manifest || echo "  (no files in this backup)"

# Optional: Upload to cloud storage
if command -v rclone >/dev/null 2>&1; then
    info "Uploading to cloud storage..."
    rclone sync "$BACKUP_DIR" remote:license-backups/ --progress 2>/dev/null || {
        info "Cloud upload failed, backup stored locally"
    }