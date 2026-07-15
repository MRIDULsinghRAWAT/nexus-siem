# Mock script to simulate directory busting web attacks
# Generates rapid HTTP 404 access log lines to test SIEM detection rules
import time
from datetime import datetime
import random

# Make sure your agent/main.py is updated to watch this file, 
# or run a second instance of the agent pointing to this log.
TARGET_LOG = "../agent/test_auth.log" 

def generate_404(ip, path):
    now = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
    # Standard Apache/Nginx log format for a 404 response
    return f'{ip} - - [{now}] "GET {path} HTTP/1.1" 404 153 "-" "Gobuster/3.1.0"\n'

paths = ["/admin", "/config.php", "/.env", "/backup.zip", "/api/v1/users", "/dashboard"]
attacker_ip = "10.0.0.99"

print("[*] Initiating Directory Busting Simulation (Gobuster)...")

with open(TARGET_LOG, "a") as f:
    for _ in range(25): # Quickly spamming 25 requests
        path = random.choice(paths)
        log_entry = generate_404(attacker_ip, path)
        f.write(log_entry)
        f.flush()
        print(f"[Simulated 404] {path}")
        time.sleep(0.1) # Extreme speed to trigger correlation rule

print("[*] Web recon payload delivered. Check your SIEM!")