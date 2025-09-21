from config import Config
import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

def get_db_connection():
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "", 1)
    else:
        db_path = db_uri  # fallback, may need more logic for other DBs
    conn = sqlite3.connect(db_path)
    return conn

@contextmanager
def get_db_connection_context():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database with tables and indexes."""
    with get_db_connection_context() as conn:
        c = conn.cursor()
        
        # Products table
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                max_devices INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Licenses table
        c.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                product_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                device_id TEXT,
                FOREIGN KEY(product_id) REFERENCES products (id)
            )
        ''')
        
        # Usage logs table
        c.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,
                user_agent TEXT,
                response_status TEXT
            )
        ''')
        
        # Indexes for performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(key)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_licenses_product ON licenses(product_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_license ON usage_logs(license_key)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_logs_ip ON usage_logs(ip_address)')
        
        conn.commit()

def get_database_size():
    """Get the size of the database file in MB."""
    db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    if os.path.exists(db_path):
        return round(os.path.getsize(db_path) / (1024 * 1024), 2)
    return 0