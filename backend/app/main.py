# Main API entrypoint for Flask/FastAPI & WebSockets
# Regex parser to transform raw text/syslog into JSON objects
from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
import datetime
from app.core.parser import parse_log
from app.core.correlation_engine import CorrelationEngine
from app.database.db_client import init_db, insert_log, insert_alert
from app.api.logs import logs_bp
from app.api.alerts import alerts_bp
from app.soar.blocker import block_ip, unblock_ip, get_blocked_ips
from app.soar.geoip import get_ip_location

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database on startup
init_db()
engine = CorrelationEngine()
app.register_blueprint(logs_bp)
app.register_blueprint(alerts_bp)

# Ingest Log API (Port 5000 fallback / HTTP receiver)
@app.route('/api/ingest', methods=['POST'])
def ingest_log():
    data = request.json
    raw_log = data.get("raw_log", "")
    agent_host = data.get("agent_host", "localhost")
    
    # 1. Parse Data
    parsed_data = parse_log(raw_log)
    parsed_data["agent_host"] = agent_host
    
    # 2. Save to Database
    insert_log(parsed_data)
    
    # 3. Stream to UI
    socketio.emit('new_log', parsed_data)
    
    # 4. Evaluate Rules & Trigger Alerts
    alert = engine.evaluate(parsed_data)
    if alert:
        print(f"[!!!] ALERT TRIGGERED: {alert['alert_title']} from {alert['source_ip']}")
        insert_alert(alert) # Save alert to DB
        socketio.emit('new_alert', alert)
        
        # Trigger SOAR Active Defense blocker
        source_ip = alert.get("source_ip")
        if source_ip:
            blocked = block_ip(source_ip, f"Correlation rule trigger: {alert['alert_title']}")
            if blocked:
                socketio.emit('ip_blocked', {
                    "ip": source_ip,
                    "blocked_at": datetime.datetime.now().isoformat(),
                    "reason": alert['alert_title'],
                    "location": get_ip_location(source_ip)
                })
        
    return jsonify({"status": "success"}), 200

# ----------------- SOAR Incident Response Endpoints -----------------

@app.route('/api/soar/blocked', methods=['GET'])
def get_soar_blocked_ips():
    """Fetches list of all currently active firewall blocks."""
    return jsonify(get_blocked_ips())

@app.route('/api/soar/unblock', methods=['POST'])
def request_soar_unblock():
    """API endpoint to manually lift an IP block from the firewall."""
    data = request.json or {}
    ip = data.get("ip")
    if not ip:
        return jsonify({"error": "Missing IP parameter"}), 400
        
    success = unblock_ip(ip)
    if success:
        # Notify frontend UI to remove from blocklist card in real-time
        socketio.emit('ip_unblocked', {"ip": ip})
        return jsonify({"status": "success", "message": f"Successfully unblocked {ip}"}), 200
    return jsonify({"error": f"IP {ip} was not found in blocklist"}), 404

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)