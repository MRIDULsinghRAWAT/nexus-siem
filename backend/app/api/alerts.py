# API endpoints for fetching historical alerts
from flask import Blueprint, jsonify
import sqlite3
import os

alerts_bp = Blueprint('alerts', __name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "siem.db")

@alerts_bp.route('/api/alerts', methods=['GET'])
def get_historical_alerts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, title, severity, source_ip, count FROM alerts ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    
    alerts = [{"timestamp": r[0], "alert_title": r[1], "severity": r[2], "source_ip": r[3], "trigger_count": r[4]} for r in rows]
    return jsonify(alerts)