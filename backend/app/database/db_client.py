# Database client wrapper for log and alert storage using SQLite
# Optimized for high-throughput scaling using Write-Ahead Logging (WAL) and an async write-queue.
import sqlite3
import os
import queue
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), "siem.db")

# Thread-safe write queue
write_queue = queue.Queue()

def get_db_connection():
    """Establishes database connection and configures performance tuning pragmas."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # Enable WAL mode: allows concurrent reading while writing is in progress
    conn.execute("PRAGMA journal_mode=WAL;")
    # Set synchronous flag to NORMAL: safe database commit speed with WAL
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """Creates tables if they don't exist and runs migrations if old columns are missing."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Create tables with the normalized schema
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 timestamp TEXT, 
                 event_type TEXT, 
                 source_ip TEXT, 
                 user_name TEXT, 
                 severity TEXT, 
                 raw TEXT,
                 agent_host TEXT
                 )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 timestamp TEXT, 
                 title TEXT, 
                 severity TEXT, 
                 source_ip TEXT, 
                 count INTEGER
                 )''')
    
    # 2. Check logs table columns and dynamically migrate if old database exists
    c.execute("PRAGMA table_info(logs)")
    existing_columns = [col[1] for col in c.fetchall()]
    
    if "user_name" not in existing_columns:
        c.execute("ALTER TABLE logs ADD COLUMN user_name TEXT")
        print("[*] Database Migration: Added 'user_name' column to logs table.")
        
    if "severity" not in existing_columns:
        c.execute("ALTER TABLE logs ADD COLUMN severity TEXT")
        print("[*] Database Migration: Added 'severity' column to logs table.")
        
    if "agent_host" not in existing_columns:
        c.execute("ALTER TABLE logs ADD COLUMN agent_host TEXT")
        print("[*] Database Migration: Added 'agent_host' column to logs table.")
        
    conn.commit()
    conn.close()

# ----------------- Async Database Write Queue Worker -----------------

def db_writer_worker():
    """Background worker thread that serializes database write tasks."""
    while True:
        task = write_queue.get()
        if task is None:
            break
        
        func, args = task
        try:
            conn = get_db_connection()
            func(conn, *args)
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[!] Database async write error: {e}")
        finally:
            write_queue.task_done()

# Start background daemon writer thread on load
writer_thread = threading.Thread(target=db_writer_worker, daemon=True)
writer_thread.start()

# ----------------- Write Tasks to be Queued -----------------

def _do_insert_log(conn, log_data):
    c = conn.cursor()
    c.execute("""INSERT INTO logs (timestamp, event_type, source_ip, user_name, severity, raw, agent_host) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)""", 
              (
                  log_data.get('timestamp'), 
                  log_data.get('event_type'), 
                  log_data.get('source_ip'), 
                  log_data.get('user'), 
                  log_data.get('severity'), 
                  log_data.get('raw'),
                  log_data.get('agent_host', 'localhost')
              ))

def _do_insert_alert(conn, alert_data):
    c = conn.cursor()
    c.execute("""INSERT INTO alerts (timestamp, title, severity, source_ip, count) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (
                  alert_data.get('timestamp'), 
                  alert_data.get('alert_title'), 
                  alert_data.get('severity'), 
                  alert_data.get('source_ip'), 
                  alert_data.get('trigger_count')
              ))

# Public API interfaces (Non-blocking queue inserts)

def insert_log(log_data):
    """Queues log insertion asynchronously without blocking API threads."""
    write_queue.put((_do_insert_log, (log_data,)))

def insert_alert(alert_data):
    """Queues alert insertion asynchronously without blocking API threads."""
    write_queue.put((_do_insert_alert, (alert_data,)))