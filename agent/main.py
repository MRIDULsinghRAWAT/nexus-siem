# Agent main service daemon
# Monitors multiple configured log files concurrently and forwards log entries to the SIEM backend
import time
import os
import json
import requests
import threading
import queue
from utils.file_watcher import watch_file

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".offline_cache.json")

# Thread-safe queue for logs to be shipped
ship_queue = queue.Queue()
cache_lock = threading.Lock()

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Error loading config.json: {e}")
    return {
        "backend_url": "http://127.0.0.1:5000/api/ingest",
        "target_logs": [],
        "poll_interval_seconds": 0.5
    }

def load_offline_cache():
    with cache_lock:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

def save_offline_cache(logs):
    with cache_lock:
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(logs, f)
        except Exception as e:
            print(f"[!] Error saving offline cache: {e}")

def watch_log_file(filepath, log_type, poll_interval):
    print(f"[+] Watcher started for {filepath} (Type: {log_type})")
    for line in watch_file(filepath, poll_interval):
        # Package the log entry with extra host and type metadata
        log_payload = {
            "raw_log": line,
            "log_type": log_type,
            "agent_host": os.environ.get("COMPUTERNAME", "localhost")
        }
        ship_queue.put(log_payload)

# TLS Certificate Paths for secure ingestion
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(os.path.dirname(AGENT_DIR), "certs")
CLIENT_CERT = os.path.join(CERT_DIR, "client.crt")
CLIENT_KEY = os.path.join(CERT_DIR, "client.key")
CA_CERT = os.path.join(CERT_DIR, "ca.crt")

def post_log(backend_url, log_payload):
    """Sends log payload over secure HTTPS (mTLS) if configured, or falls back to plain HTTP."""
    if backend_url.startswith("https://") and os.path.exists(CLIENT_CERT):
        return requests.post(
            backend_url, 
            json=log_payload, 
            timeout=3, 
            verify=CA_CERT, 
            cert=(CLIENT_CERT, CLIENT_KEY)
        )
    return requests.post(backend_url, json=log_payload, timeout=3)

def log_shipper(backend_url):
    print(f"[+] Shipper thread started targeting: {backend_url}")
    
    # Try to flush any cached offline logs on boot
    flush_offline_logs(backend_url)
    
    while True:
        try:
            log_payload = ship_queue.get()
            
            try:
                response = post_log(backend_url, log_payload)
                if response.status_code == 200:
                    # Successfully sent. Now check if we can flush offline cache.
                    flush_offline_logs(backend_url)
                else:
                    cache_log_offline(log_payload)
            except requests.RequestException as e:
                # Print connection error context (e.g. ssl handshakes) to help debug
                print(f"[!] Log delivery request failed: {e}")
                cache_log_offline(log_payload)
                
            ship_queue.task_done()
        except Exception as e:
            print(f"[!] Error in shipper loop: {e}")
            time.sleep(1)

def cache_log_offline(log_payload):
    print(f"[!] Backend unreachable. Saving log to offline cache: {log_payload['raw_log'][:40]}...")
    cached_logs = load_offline_cache()
    cached_logs.append(log_payload)
    save_offline_cache(cached_logs)

def flush_offline_logs(backend_url):
    cached_logs = load_offline_cache()
    if not cached_logs:
        return
        
    print(f"[*] Found {len(cached_logs)} offline logs. Attempting to flush...")
    successful_flushes = 0
    
    for log in list(cached_logs):
        try:
            response = post_log(backend_url, log)
            if response.status_code == 200:
                cached_logs.remove(log)
                successful_flushes += 1
            else:
                break
        except requests.RequestException:
            break
            
    save_offline_cache(cached_logs)
    if successful_flushes > 0:
        print(f"[+] Successfully flushed {successful_flushes} offline logs to backend.")

def start_agent():
    config = load_config()
    backend_url = config.get("backend_url", "http://127.0.0.1:5000/api/ingest")
    target_logs = config.get("target_logs", [])
    poll_interval = config.get("poll_interval_seconds", 0.5)

    print(f"[+] Starting Nexus SIEM Agent...")
    print(f"[*] Configuration loaded from {CONFIG_PATH}")
    print(f"[*] Backend Ingest URL: {backend_url}")

    # Start shipper daemon
    shipper_thread = threading.Thread(target=log_shipper, args=(backend_url,), daemon=True)
    shipper_thread.start()

    # Start log file watchers
    for log_config in target_logs:
        path = log_config.get("path")
        log_type = log_config.get("type", "unknown")
        
        t = threading.Thread(target=watch_log_file, args=(path, log_type, poll_interval), daemon=True)
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Agent shutting down...")

if __name__ == "__main__":
    start_agent()