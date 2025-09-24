from config import Config
import sqlite3
import os
from contextlib import contextmanager

def get_db_connection():
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    if db_uri.startswith("sqlite:///"):
        db_path = db_uri.replace("sqlite:///", "", 1)
    else:
        db_path = db_uri
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')  # Enable Write-Ahead Logging for concurrency
    return conn

@contextmanager
def get_db_connection_context():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def drop_users_table():
    """Drop the users table if it exists."""
    with get_db_connection_context() as conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS users')
        conn.commit()

def drop_licenses_table():
    """Drop the licenses table if it exists."""
    with get_db_connection_context() as conn:
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS licenses')
        conn.commit()

def insert_default_users():
    defaults_users = {('richtoolsmmo01', 'scrypt:32768:8:1$vuq23ksbmIwhZXvY$7d662a9245b86bfedd7cce8de9d30ae4a0bfdd77e654f00b03084128cbc22ba840abd169d3dcba86a2b703ae85b423e8195f4b22181004fdecefa779c7cca557', 'Admin', 'User', 'admin'),
                      ('huytoolsmmo01', 'scrypt:32768:8:1$bE5kDLcULDhLavTV$9f9e07ddb32971b90d3da970ce0facc2b5c05fca0f0083fe6c7ed126761772b11e9041fa1b73efca7b38741197edb078f94f33b724cc1d3a7aeef5849b77b442', 'Admin', 'User', 'user'),
                      ('huytoolsmmo01_admin','scrypt:32768:8:1$3BxwPe2lql01l0dV$2a587946f02b13bdd84c20be01d022d19dc66253fa522e5babe37b869760990b19c665dd31cb8031d551a4d19a4f22594c46234db3cebb76b154a2dd03790357','Admin','User','user'),
                      ('richtoolsmmo.huy', 'scrypt:32768:8:1$JrMHEg79KGrnsXvS$d59b6ddec115ed8bd2e159b2e24b9de0f55bf863f73cf68021635966084a64a689413bacd1f57c904a62a3014ee31474eb7ee18ef68b899812c664dec5cc5cf2','Test','User','user'),
                      ('richtoolsmmo_backup', 'scrypt:32768:8:1$guRm0sq7jMnOK714$bee8de766c45f809ac9bc86072d2f43578ba2965f89b6eaff6ec40b425b89bf122c683e743e9606c7afc4c1aa6d90d8387a1c36f933d10719843d9f48784ad5b', 'Default', 'Admin', 'user')}
    with get_db_connection_context() as conn:
        c = conn.cursor()
        for user in defaults_users:
            try:
                c.execute('''
                    INSERT INTO users (username, password, first_name, last_name, role)
                    VALUES (?, ?, ?, ?, ?)
                ''', user)
            except sqlite3.IntegrityError:
                pass  # User already exists
        conn.commit()

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
                credit_number TEXT DEFAULT 'None',
                machine_code TEXT DeFAULT 'None',
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

        # Users table
        c.execute('''
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