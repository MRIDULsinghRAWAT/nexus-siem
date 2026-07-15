import re
from datetime import datetime

def parse_log(raw_log):
    # 1. SSH Failed Login Regex (Attack)
    ssh_failed_pattern = r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+)"
    ssh_failed_match = re.search(ssh_failed_pattern, raw_log)
    if ssh_failed_match:
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": "failed_login",
            "user": ssh_failed_match.group("user"),
            "source_ip": ssh_failed_match.group("ip"),
            "severity": "medium",
            "raw": raw_log
        }

    # 2. SSH Successful Login Regex (Normal Traffic)
    ssh_success_pattern = r"Accepted password for (?:invalid user )?(?P<user>\S+) from (?P<ip>\S+)"
    ssh_success_match = re.search(ssh_success_pattern, raw_log)
    if ssh_success_match:
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": "successful_login",
            "user": ssh_success_match.group("user"),
            "source_ip": ssh_success_match.group("ip"),
            "severity": "info",
            "raw": raw_log
        }

    # 3. Apache/Nginx Web Log Regex (Covers all status codes like 200, 404, etc.)
    web_pattern = r'(?P<ip>\S+) \S+ \S+ \[.*?\] "\S+ (?P<path>\S+) HTTP.*?" (?P<status>\d+)'
    web_match = re.search(web_pattern, raw_log)
    if web_match:
        status_code = web_match.group("status")
        is_404 = (status_code == "404")
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": f"http_{status_code}",
            "path": web_match.group("path"),
            "source_ip": web_match.group("ip"),
            "severity": "low" if is_404 else "info",
            "raw": raw_log
        }

    # 4. Linux System Cron Log Regex (Normal System Activity)
    cron_pattern = r"CRON\[\d+\]: \((?P<user>[^)]+)\) CMD"
    cron_match = re.search(cron_pattern, raw_log)
    if cron_match:
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": "cron_job",
            "user": cron_match.group("user"),
            "source_ip": "127.0.0.1", # Internal local execution
            "severity": "info",
            "raw": raw_log
        }
    
    # 5. Generic fallback
    return {
        "timestamp": datetime.now().isoformat(),
        "event_type": "unknown",
        "source_ip": "127.0.0.1",
        "raw": raw_log
    }