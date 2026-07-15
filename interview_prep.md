# Interview Preparation Guide: Nexus-SIEM & SOAR Security Framework

This document is designed to help you explain this project confidently in technical interviews. It covers the core elevator pitch, key architecture pillars, problem statements, technology choices, and the top 25 technical interview questions you are likely to be asked.

---

## 1. Project Summary (5-6 Line Pitch)
**Nexus-SIEM** is a lightweight, high-performance Security Information and Event Management (SIEM) and Security Orchestration, Automation, and Response (SOAR) sandbox environment. It uses a multi-threaded endpoint agent to securely ship system logs to a central server using strict **Mutual TLS (mTLS)** validation, preventing spoofing and man-in-the-middle attacks. The backend features an asynchronous database queue tuned with **SQLite Write-Ahead Logging (WAL)** to handle high EPS (Events Per Second) injection without lock contention. Received logs are parsed in real-time and evaluated by a behavioral correlation engine which triggers automated firewall rules (SOAR) to block attacking IPs. All events, active defense statuses, and logs are displayed dynamically on a real-time React dashboard powered by **Socket.io WebSockets**.

---

## 2. Problem Statement & Solution

### The Problems:
1. **Unsecured Log Shipping:** Standard log shippers send logs in cleartext or without client verification. Attackers on the network can easily intercept, modify, or spoof logs to cover their tracks.
2. **Database Ingestion Bottlenecks:** Centralized SIEMs receive thousands of logs per second. Standard relational databases lock up under concurrent write operations, causing packet loss and crashed server threads.
3. **Slow Incident Response:** Standard monitoring setups only alert analysts, leaving a time gap between detection and mitigation where attackers can complete their breach.

### The Solutions:
1. **mTLS Log Pipeline:** Enforces client-certificate checks against a private Root CA, guaranteeing only verified endpoint agents can ingest logs.
2. **Asynchronous Thread-safe DB Queue + WAL:** Organizes incoming writes sequentially through a queue worker and uses SQLite in WAL mode to allow concurrent reads and writes without thread crashes.
3. **Automated Active Defense (SOAR):** Instantly triggers a firewall block rule when a threat (like an SSH brute-force attempt) is correlated, immediately neutralizing the threat.

---

## 3. Technology Stack & Why It Was Used

| Technology | Role in Project | Why We Used It |
| :--- | :--- | :--- |
| **React 18 & Vite** | Frontend Dashboard UI | Provides a fast, modern component-based single-page UI optimized for live state updates. |
| **Socket.io** | WebSocket Communication | Enables instant, bi-directional event streaming from backend to frontend without polling overhead. |
| **Recharts** | Metrics Visualization Charts | Lightweight, SVG-based charting library that renders complex trends and stats smoothly. |
| **Flask (Python)** | Backend REST APIs | Minimalist web framework, perfect for building flexible APIs and running background daemon threads. |
| **SQLite (WAL Mode)** | Primary Log Database | Highly portable, relational file database. Tuned with Write-Ahead Logging (WAL) to run fast concurrent reads and writes. |
| **Python Cryptography** | PKI Certificate Authority | Used to programmatically sign X509 certificates for strict agent/server authentication. |
| **YAML** | Correlation Engine Rules | Human-readable configuration format, making it easy for security teams to update threat signatures. |

---

## 4. Top 25 Interview Questions & Answers

### Category A: General Architecture & Flow

#### Q1: Can you explain the end-to-end data flow when a log is generated?
**Answer:** 
1. The **Traffic Simulator** appends mock events into a system log file (e.g. `test_auth.log`).
2. The **Shipper Agent** running on the client machine tails the file using an unbuffered file watcher.
3. The agent packages the raw text line with metadata and sends a POST request to the backend `/api/ingest` over an mTLS-secured tunnel on port `5001`.
4. The **Backend Ingest Server** validates the client certificate, parses the log using regex, inserts it into the database queue, and pushes it to the correlation engine.
5. If the correlation engine detects a threat (e.g. 5 failed login attempts in 10 seconds), it generates an alert, writes it to the database, and flags the IP as blocked.
6. Real-time updates are sent to the **React Frontend** via WebSockets (`Socket.io`) to update the active graphs, logs, and firewall blocks immediately.

#### Q2: What is the difference between SIEM and SOAR in the context of your project?
**Answer:** 
* **SIEM** (Security Information and Event Management) handles log collection, parsing, storage, and real-time visualization (the charts, trend lines, and live logs table).
* **SOAR** (Security Orchestration, Automation, and Response) handles the automation. In this project, when the correlation engine flags an alert, the SOAR system automatically triggers a firewall block rule (`block_ip`) to ban the attacking IP and exposes an API endpoint to allow analysts to manually release (unblock) the IP.

#### Q3: Why did you separate the ingestion API on Port 5001 from the Dashboard API on Port 5000?
**Answer:** 
Port `5001` is configured with strict client certificate verification (`ssl.CERT_REQUIRED`) for **mTLS**. If we ran everything on one port, the browser would prompt the human operator for a client certificate when trying to load the dashboard page. Splitting the ports keeps the frontend dashboard public/accessible over standard HTTP (port 5000) while keeping the log ingestion endpoint highly secure (port 5001).

#### Q4: How does the agent handle log tailing without eating up CPU cycles?
**Answer:**
The agent implements a file watcher that yields lines as they appear. It opens the target file, seeks to the end on start (to avoid shipping historical logs), and enters a polling loop. If no new data is found, it sleeps for a configured fraction of a second (e.g., `0.5s`) before checking again. This prevents CPU spinning.

---

### Category B: mTLS & PKI Security

#### Q5: What is mTLS and why is it necessary for a SIEM system?
**Answer:**
Mutual TLS (mTLS) is a process where both the client and server validate each other’s cryptographic certificates during the TLS handshake. It is critical for a SIEM because standard HTTPS only validates the server. mTLS ensures that *only* certified endpoints within our private PKI infrastructure can ingest logs, preventing rogue actors from sending fake logs or spoofing system activity.

#### Q6: How does the server verify client certificates in Python?
**Answer:**
We use Python's built-in `ssl` library to wrap the Flask socket context. We load the server's certificate chain and private key, load our private Root CA certificate (`ca.crt`) using `load_verify_locations`, and set `context.verify_mode = ssl.CERT_REQUIRED`. During the handshake, if the client fails to present a certificate signed by the Root CA, the connection is instantly closed before any HTTP data is read.

#### Q7: What happens if an attacker steals a client certificate? How can you mitigate this?
**Answer:**
If a client certificate is compromised, the attacker can spoof logs. In a production environment, this is mitigated by implementing a **Certificate Revocation List (CRL)** or **OCSP (Online Certificate Status Protocol)** check on the backend. When a certificate is reported stolen, the server rejects its serial number even if it is signed by the CA.

#### Q8: How does the shipper agent handle network drops? Do logs get lost?
**Answer:**
No. The shipper agent implements an **offline cache**. If a log post request fails due to a network connection timeout, the agent catches the exception, saves the log payload into a local JSON cache file (`.offline_cache.json`), and periodically retries. Once the server is reachable, it flushes the offline cache in order before resuming live shipping.

---

### Category C: Database Tuning & Scaling

#### Q9: What database engine did you use, and what tuning did you perform for high EPS?
**Answer:**
We used **SQLite**. While SQLite is simple, we tuned it for high EPS by enabling **WAL (Write-Ahead Logging)** mode. In standard rollback journal mode, writing locks the entire database. In WAL mode, SQLite writes changes to a separate journal file, allowing readers to read the main database file concurrently without blocking or database locked errors.

#### Q10: Why did you write an asynchronous database queue?
**Answer:**
Even with WAL mode, concurrent write queries from multiple incoming threads (since Flask spawns a thread per request) can crash due to locking collisions. To solve this, we created a thread-safe Python `queue.Queue`. When a log arrives, it is instantly pushed to the memory queue. A single background worker thread processes the queue sequentially, batching inserts into the database. This guarantees thread safety and keeps response times fast.

#### Q11: How do you prevent the database file from growing infinitely?
**Answer:**
In a production deployment, we would implement a **log retention and rotation policy**. This involves a cron job that runs a database pruning script to delete logs older than a specific date (e.g., `DELETE FROM logs WHERE timestamp < date('now', '-30 days')`) and runs the `VACUUM` command to reclaim unused space.

---

### Category D: Correlation Rules & Threat Detection

#### Q12: How does the Correlation Rules Engine work in your backend?
**Answer:**
The correlation engine loads detection rules from YAML files (e.g., detecting brute-force or directory busting). It parses incoming logs, updates a rolling window of events mapped to their source IP, and checks if the threshold count has been breached within the time window. For example: `5 failed login events from the same IP within 10 seconds`.

#### Q13: Explain the data structure used to track events inside the correlation engine.
**Answer:**
The correlation engine uses an in-memory dictionary of lists, keyed by the source IP address: `self.windows = defaultdict(list)`. For each incoming event, it appends the timestamp of the event. It then cleans the list by removing any timestamps older than the configured window size (e.g., `now - 10s`). The length of the cleaned list represents the active event frequency.

#### Q14: How does the SOAR system block an IP address?
**Answer:**
When an alert is triggered, the engine calls `block_ip(ip, reason)`. In this sandbox, this inserts the IP, timestamp, and rule violation details into a SQLite table (`blocked_ips`). In a production setting, this helper function would also trigger a system script to update the local OS firewall (like executing `iptables -A INPUT -s <IP> -j DROP` or API calls to a cloud security group).

#### Q15: What is the risk of keeping the correlation window entirely in-memory?
**Answer:**
If the backend process crashes or restarts, all active state tracking windows are lost. In a production environment, this is solved by using a fast, persistent in-memory store like **Redis** with TTL (Time-To-Live) on keys to track sliding window counters.

---

### Category E: Frontend & WebSockets

#### Q16: Why did you choose WebSockets (Socket.io) instead of REST polling?
**Answer:**
REST polling requires the frontend to query the backend every 1-2 seconds, creating massive network overhead, database read queries, and latency. WebSockets establish a single, long-running TCP connection. The backend pushes updates to the dashboard only when a new log is received or an alert is fired, resulting in near-zero latency and minimal server load.

#### Q17: How did you prevent the React state from lagging with a high volume of live logs?
**Answer:**
In App.jsx, when a `new_log` event is received via WebSockets, we prepend the log to the state array and slice the array to a maximum of 50 items (`.slice(0, 50)`). This prevents the DOM tree from growing indefinitely, which would otherwise lag the browser rendering thread.

#### Q18: How does the "Notice vs Warning" Syslog KPI work?
**Answer:**
We filter the logs array by their severity levels. Severity labels like `info` or `low` map to "Notice" metrics, while `medium`, `high`, or `critical` map to "Warning" metrics. The frontend calculates these lengths dynamically on the fly to update the KPI metrics.

---

### Category F: Production Deployment & Best Practices

#### Q19: How would you deploy the React frontend in a production environment?
**Answer:**
I would build the frontend static assets using `npm run build` to output HTML, JS, and CSS files. Then, I would host these files using a production-grade web server like **Nginx**. I would configure Nginx to serve the static assets and act as a reverse proxy, forwarding requests to `/api` and `/socket.io` to the Gunicorn WSGI backend.

#### Q20: How would you run the Flask backend in production?
**Answer:**
Instead of Flask’s built-in development server (which is single-threaded and unsafe), I would use **Gunicorn** with the **Eventlet** worker class:
`gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5000 run:app`
This supports high concurrency and handles the long-running WebSocket connections efficiently.

#### Q21: How would you secure the backend REST APIs from unauthorized access?
**Answer:**
I would implement **Role-Based Access Control (RBAC)** using JWT (JSON Web Tokens) or session-based cookies. Any dashboard request to release an IP (`/api/soar/unblock`) would require a valid admin JWT header, ensuring only authorized SOC analysts can modify firewall blocklists.

#### Q22: What are some indicators of a "False Positive" in the correlation rules? How do we fine-tune it?
**Answer:**
A false positive could be an automated backup script that logs in via SSH and fails once due to an expired key rotation. To fine-tune this, we can add exception rules (e.g. whitelisting internal subnets like `10.0.0.0/24` from block triggers) or increase the window threshold values in the YAML detection rules.

#### Q23: Why do we use SQLite WAL mode instead of standard MySQL or PostgreSQL in this project?
**Answer:**
SQLite WAL is ideal for a lightweight, self-contained project sandbox because it requires zero installation or database server management. For an enterprise-scale SIEM, we would migrate the database layer to a high-throughput time-series database (like **Elasticsearch**, **ClickHouse**, or **TimescaleDB**) designed specifically for querying billions of log files.

#### Q24: How does the regex parser process logs?
**Answer:**
The parser runs the raw log string against pre-defined regular expressions. It matches syslog patterns (extracting timestamps, hostnames, service names, PIDs, and messages) and web logs (extracting IP, path, response codes, bytes sent, and user-agent). If matched, it structures the raw string into a structured JSON dictionary.

#### Q25: How would you scale the log ingestion pipeline if you had 10,000 agents shipping logs?
**Answer:**
I would place a message broker like **Apache Kafka** or **RabbitMQ** in front of the ingestion pipeline. Instead of shipping logs directly to the Flask database queue, agents would send them to Kafka topic partitions. Multiple backend worker microservices would then consume from Kafka and write to the database in batches, absorbing high spikes in traffic.
