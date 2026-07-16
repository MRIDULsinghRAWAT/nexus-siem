# Script runner/entrypoint to spin up backend with HTTPS and strict mTLS log ingestion
import ssl
import os
import threading
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from app.main import app, socketio, engine
from app.core.parser import parse_log
from app.database.db_client import insert_log, insert_alert
from app.soar.blocker import block_ip
from app.soar.geoip import get_ip_location

# Paths to generated TLS certificates
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "certs")

# ----------------- 1. Define mTLS Log Ingestion App -----------------
ingest_app = Flask("secure_log_ingester")
CORS(ingest_app)

@ingest_app.route('/api/ingest', methods=['POST'])
def ingest_log_secure():
    """Secure endpoint that accepts raw logs over client-verified mTLS tunnels."""
    data = request.json
    raw_log = data.get("raw_log", "")
    agent_host = data.get("agent_host", "localhost")
    
    # Parse log metadata
    parsed_data = parse_log(raw_log)
    parsed_data["agent_host"] = agent_host
    
    # Asynchronously save to Database (using scaling WAL batch queue)
    insert_log(parsed_data)
    
    # Broadcast to dashboard UI
    socketio.emit('new_log', parsed_data)
    
    # Run correlation matching
    alert = engine.evaluate(parsed_data)
    if alert:
        print(f"[!!!] ALERT TRIGGERED (mTLS): {alert['alert_title']} from {alert['source_ip']}")
        insert_alert(alert)
        socketio.emit('new_alert', alert)
        
        # Trigger SOAR Active Defense blocker
        source_ip = alert.get("source_ip")
        if source_ip:
            blocked = block_ip(source_ip, f"mTLS Ingest Correlation trigger: {alert['alert_title']}")
            if blocked:
                socketio.emit('ip_blocked', {
                    "ip": source_ip,
                    "blocked_at": datetime.datetime.now().isoformat(),
                    "reason": alert['alert_title'],
                    "location": get_ip_location(source_ip)
                })
        
    return jsonify({"status": "success"}), 200

def run_mtls_ingest_server():
    """Runs the secure log receiver on port 5001, enforcing client authentication."""
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certfile=os.path.join(CERT_DIR, "server.crt"),
        keyfile=os.path.join(CERT_DIR, "server.key")
    )
    # Load CA certificate to verify client keys
    context.load_verify_locations(cafile=os.path.join(CERT_DIR, "ca.crt"))
    context.verify_mode = ssl.CERT_REQUIRED
    
    print("[*] Starting Secure Log Ingestion Service (mTLS) on port 5001...")
    ingest_app.run(host='0.0.0.0', port=5001, ssl_context=context, debug=False, use_reloader=False)

# ----------------- 2. Main Entrypoint -----------------
if __name__ == '__main__':
    # Start thread for mTLS secure log receiver (port 5001)
    mtls_thread = threading.Thread(target=run_mtls_ingest_server, daemon=True)
    mtls_thread.start()
    
    print("[*] Starting NexusSIEM UI Dashboard Backend (HTTP) on port 5000...")
    # Run UI API server over HTTP to prevent browser self-signed cert blocks
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)