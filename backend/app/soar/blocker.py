# SOAR Automated Response Blocker Module
# Simulates standard enterprise firewalls or security group rules by managing an active blocked IP list.
import os
import json
import datetime

BLOCKED_FILE = os.path.join(os.path.dirname(__file__), "blocked_ips.json")

def load_blocked_ips():
    """Reads blocked IPs from file, returning a list of dicts."""
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_blocked_ips(blocked_list):
    """Saves list of blocked IPs back to disk."""
    try:
        with open(BLOCKED_FILE, 'w') as f:
            json.dump(blocked_list, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving blocked IPs database: {e}")

def block_ip(ip, reason="Automated SIEM correlation rule trigger"):
    """Blocks an IP address if it is not already in the blocklist."""
    if not ip or ip in ("127.0.0.1", "localhost", "-"):
        return False # Never block internal loopbacks or empty values
        
    blocked_ips = load_blocked_ips()
    # Check if already blocked
    for item in blocked_ips:
        if item["ip"] == ip:
            return False
            
    # Add new block record
    block_record = {
        "ip": ip,
        "blocked_at": datetime.datetime.now().isoformat(),
        "reason": reason,
        "status": "ACTIVE"
    }
    blocked_ips.append(block_record)
    save_blocked_ips(blocked_ips)
    print(f"[🛡️ SOAR Active Defense] BLOCKED malicious IP: {ip} | Reason: {reason}")
    return True

def unblock_ip(ip):
    """Removes an IP address from the blocklist (manual or automatic unblock)."""
    blocked_ips = load_blocked_ips()
    initial_length = len(blocked_ips)
    
    # Filter out target IP
    blocked_ips = [item for item in blocked_ips if item["ip"] != ip]
    
    if len(blocked_ips) < initial_length:
        save_blocked_ips(blocked_ips)
        print(f"[🛡️ SOAR Active Defense] UNBLOCKED IP: {ip}")
        return True
    return False

def is_ip_blocked(ip):
    """Returns True if the IP is active in the firewall blocklist."""
    blocked_ips = load_blocked_ips()
    return any(item["ip"] == ip for item in blocked_ips)

def get_blocked_ips():
    """Returns the list of all blocked IPs."""
    return load_blocked_ips()
