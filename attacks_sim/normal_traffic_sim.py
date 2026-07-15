# Mock script to simulate continuous, non-malicious background logs
# Mimics normal server noise (successful logins, cron jobs, web traffic) 
# so your SIEM dashboard runs live in real-time without active attacks.
import time
import random
import os
from datetime import datetime

# Log file targets (matching agent configuration)
AUTH_LOG = "../agent/test_auth.log"
WEB_LOG = "../agent/test_web.log"

# Mock dataset for realistic generation
users = ["mridul", "admin", "db_backup", "developer", "system_daemon"]
ips = ["192.168.1.50", "192.168.1.12", "10.0.0.15", "172.16.5.9", "127.0.0.1"]
web_pages = ["/home", "/dashboard", "/about", "/api/v1/metrics", "/static/logo.png", "/contact"]
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Firefox/113.0"
]

def generate_successful_login():
    now = datetime.now().strftime("%b %d %H:%M:%S")
    user = random.choice(users)
    ip = random.choice(ips)
    port = random.randint(49152, 65535)
    pid = random.randint(10000, 99999)
    return f"{now} server sshd[{pid}]: Accepted password for {user} from {ip} port {port} ssh2\n", AUTH_LOG

def generate_cron_job():
    now = datetime.now().strftime("%b %d %H:%M:%S")
    pid = random.randint(10000, 99999)
    actions = [
        "session opened for user root",
        "(root) CMD (   /usr/local/bin/log_rotation.sh > /dev/null 2>&1)",
        "(syslog) CMD (   /usr/sbin/logcheck)",
        "session closed for user root"
    ]
    action = random.choice(actions)
    return f"{now} server CRON[{pid}]: {action}\n", AUTH_LOG

def generate_web_traffic():
    ip = random.choice(ips)
    now = datetime.now().strftime("%d/%b/%Y:%H:%M:%S +0000")
    page = random.choice(web_pages)
    bytes_sent = random.randint(200, 15000)
    agent = random.choice(user_agents)
    return f'{ip} - - [{now}] "GET {page} HTTP/1.1" 200 {bytes_sent} "-" "{agent}"\n', WEB_LOG

log_generators = [
    generate_successful_login,
    generate_cron_job,
    generate_web_traffic
]

print("[*] Initiating Background Noise Simulator...")
print(f"[*] Appending normal system events to {AUTH_LOG} and {WEB_LOG}")
print("[*] Press CTRL+C to terminate.")

# Ensure files exist before appending
for log_file in [AUTH_LOG, WEB_LOG]:
    if not os.path.exists(log_file):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        open(log_file, 'a').close()

try:
    while True:
        # Choose a random log generator
        generator = random.choice(log_generators)
        log_line, filepath = generator()
        
        # Write to log file
        with open(filepath, "a") as f:
            f.write(log_line)
            f.flush()
            
        print(f"[Ingested Normal Log] {log_line.strip()[:80]}...")
        
        # Wait a random short duration between log updates (0.5 to 2.0 seconds)
        time.sleep(random.uniform(0.5, 2.0))
        
except KeyboardInterrupt:
    print("\n[*] Background Noise Simulator stopped.")
