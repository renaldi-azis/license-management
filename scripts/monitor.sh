#!/bin/bash

# License Server Health Monitor

set -e

# Configuration
API_URL="http://localhost:5000"
CHECK_INTERVAL=30
MAX_FAILURES=3
NOTIFICATION_EMAIL="admin@example.com"
LOG_FILE="/var/log/license-monitor.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local subject="$1"
    local message="$2"
    echo "$message" | mail -s "License Server Alert: $subject" "$NOTIFICATION_EMAIL"
    log "ALERT: $subject - $message"
}

check_health() {
    local endpoint="$1"
    local description="$2"
    
    if curl -s -f -m 10 "$API_URL$endpoint" > /dev/null; then
        log "$description - OK"
        return 0
    else
        log "$description - FAILED"
        return 1
    fi
}

check_database() {
    python3 -c "
import sqlite3
from contextlib import contextmanager
import sys

@contextmanager
def get_connection():
    conn = sqlite3.connect('data/licenses.db')
    try:
        yield conn
    finally:
        conn.close()

try:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM products')
        count = c.fetchone()[0]
        sys.exit(0)
except Exception as e:
    sys.exit(1)
" > /dev/null 2>&1
}

check_redis() {
    if command -v redis-cli >/dev/null 2>&1 && pgrep redis-server >/dev/null 2>&1; then
        if redis-cli ping > /dev/null 2>&1; then
            log "Redis - OK"
            return 0
        else
            log "Redis - FAILED"
            return 1
        fi
    else
        log "Redis not running or not installed, skipping Redis check"
        return 0
    fi
}

main() {
    log "Starting License Server health check..."
    
    local failures=0
    
    # Check API endpoints
    if ! check_health "/health" "API Health"; then ((failures++)); fi
    if ! check_health "/api/products" "Products API"; then ((failures++)); fi
    if ! check_health "/api/licenses/stats" "Licenses API"; then ((failures++)); fi
    
    # Check database
    if ! check_database; then
        log "Database check - FAILED"
        ((failures++))
    fi
    
    # Check Redis
    if ! check_redis; then
        log "Redis check - FAILED"
        ((failures++))
    fi
    
    # Alert on failures
    if [ $failures -gt 0 ]; then
        local alert_msg="Health check failed: $failures/5 checks failed

Health check details:
$(tail -n 10 "$LOG_FILE")"
        send_alert "License Server Health Alert" "$alert_msg"
        
        if [ $failures -ge $MAX_FAILURES ]; then
            log "CRITICAL: Too many failures ($failures). Manual intervention required."
            # Optional: trigger emergency restart
            # systemctl restart license-server
        fi
    else
        log "All systems healthy!"
    fi
}

# Run main function
main

# Optional: Schedule with cron
# Add to crontab: */${CHECK_INTERVAL} * * * * /path/to/monitor.sh >> /var/log/license