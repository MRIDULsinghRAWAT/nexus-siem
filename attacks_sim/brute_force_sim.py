# Mock script to simulate brute force SSH login attacks
# Generates fake failed logins into target logs to test SIEM detection rules
import time
from datetime import datetime

TARGET_LOG = "../agent/test_auth.log" # Make sure this matches your agent config

def generate_failed_login(ip, user):
    now = datetime.now().strftime("%b %d %H:%M:%S")
    # Standard Linux auth.log failed password string
    return f"{now} server sshd[40134]: Failed password for {user} from {ip} port 22 ssh2\n"

print("[*] Initiating simulated SSH brute force...")

# Simulating 8 rapid failed logins from the same IP (Triggering the >5 in 10s rule)
attacker_ip = "192.168.1.105"
target_user = "root"

with open(TARGET_LOG, "a") as f:
    for i in range(8):
        log_entry = generate_failed_login(attacker_ip, target_user)
        f.write(log_entry)
        f.flush()
        print(f"[Simulated] {log_entry.strip()}")
        time.sleep(0.5) # Half second delay between attempts

print("[*] Attack payload delivered. Check your SIEM dashboard!")