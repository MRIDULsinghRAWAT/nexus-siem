# Correlation Engine logic to evaluate rules against live log streams
from collections import defaultdict
import time
import yaml
import os

RULES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "rules_config.yaml")

class CorrelationEngine:
    def __init__(self):
        # Format: { "192.168.1.1": { "failed_login": [time1, time2], "http_404": [time1] } }
        self.history = defaultdict(lambda: defaultdict(list))
        self.rules = self.load_rules()

    def load_rules(self):
        try:
            with open(RULES_PATH, 'r') as f:
                config = yaml.safe_load(f)
                print(f"[+] Loaded {len(config.get('rules', []))} detection rules from YAML.")
                return config.get('rules', [])
        except Exception as e:
            print(f"[!] Error loading rules: {e}")
            return []

    def evaluate(self, parsed_log):
        event_type = parsed_log.get("event_type")
        ip = parsed_log.get("source_ip")
        
        if not ip or event_type == "unknown":
            return None

        current_time = time.time()
        
        for rule in self.rules:
            if rule['event_type'] == event_type:
                # Add current timestamp to the history for this IP and event type
                self.history[ip][event_type].append(current_time)
                
                # Remove timestamps older than the rule's time window
                self.history[ip][event_type] = [
                    t for t in self.history[ip][event_type] 
                    if current_time - t <= rule['time_window_seconds']
                ]
                
                # Check if threshold is breached
                if len(self.history[ip][event_type]) >= rule['threshold']:
                    self.history[ip][event_type] = [] # Clear to prevent alert spam
                    return {
                        "alert_title": rule['name'],
                        "severity": rule['severity'],
                        "source_ip": ip,
                        "trigger_count": rule['threshold'],
                        "timestamp": parsed_log["timestamp"]
                    }
        return None