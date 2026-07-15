# API endpoints for searching and filtering raw logs
from flask import Blueprint, jsonify
import sqlite3
import os

logs_bp = Blueprint('logs', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "siem.db")

@logs_bp.route('/api/logs', methods=['GET'])
def get_historical_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Fetch latest 50 logs with new normalized fields
    c.execute("SELECT timestamp, event_type, source_ip, user_name, severity, raw, agent_host FROM logs ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    
    logs = [
        {
            "timestamp": r[0], 
            "event_type": r[1], 
            "source_ip": r[2], 
            "user_name": r[3], 
            "severity": r[4], 
            "raw": r[5],
            "agent_host": r[6]
        } 
        for r in rows
    ]
    return jsonify(logs)