import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import AlertCard from './components/AlertCard';
import LiveLogTable from './components/LiveLogTable';
import { LogsTrendChart, TopDevicesChart, SeverityDonutChart, EPSSparkline } from './components/MetricChart';
import ThreatMap from './components/ThreatMap';
import './index.css';

// Dynamically resolve hostname. Connect via HTTP to dashboard backend (port 5000)
const hostname = window.location.hostname || "127.0.0.1";
const socket = io(`http://${hostname}:5000`);

export default function App() {
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [blockedIps, setBlockedIps] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [trendGrowth, setTrendGrowth] = useState("0 (0.00%)");
  const [epsVal, setEpsVal] = useState(0);
  const [epsHistory, setEpsHistory] = useState([]);
  
  const logCounterRef = useRef(0);

  // Real-time EPS Sparkline Ticker
  useEffect(() => {
    // Pre-populate sparkline history with empty points (last 30 seconds)
    const initialEPS = [];
    for (let i = 29; i >= 0; i--) {
      initialEPS.push({ time: `${i}s ago`, eps: 0 });
    }
    setEpsHistory(initialEPS);

    const ticker = setInterval(() => {
      const currentCount = logCounterRef.current;
      logCounterRef.current = 0; // Reset counter for the next second
      setEpsVal(currentCount);

      setEpsHistory(prev => {
        const nextHist = [...prev.slice(1), { time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), eps: currentCount }];
        return nextHist;
      });
    }, 1000);

    return () => clearInterval(ticker);
  }, []);

  // Fetch initial history from APIs over HTTP on load and poll periodically
  useEffect(() => {
    const fetchData = () => {
      fetch(`http://${hostname}:5000/api/logs`)
        .then(res => res.json())
        .then(data => {
          setLogs(data);
          
          // Calculate growth metric dynamically for the "All Events" KPI card
          if (data.length > 0) {
            const recentLogsCount = data.filter(l => {
              const diff = Date.now() - new Date(l.timestamp).getTime();
              return diff < 60000; // logs in the last minute
            }).length;
            const percent = ((recentLogsCount / data.length) * 100).toFixed(1);
            setTrendGrowth(`${recentLogsCount} (${percent}%)`);
          }
        })
        .catch(err => console.error("Error fetching logs:", err));

      fetch(`http://${hostname}:5000/api/alerts`)
        .then(res => res.json())
        .then(data => {
          setAlerts(data);
        })
        .catch(err => console.error("Error fetching alerts:", err));

      fetch(`http://${hostname}:5000/api/soar/blocked`)
        .then(res => res.json())
        .then(data => {
          setBlockedIps(data);
        })
        .catch(err => console.error("Error fetching blocked IPs:", err));
    };

    fetchData(); // Initial run
    const interval = setInterval(fetchData, 1000); // 1-second auto-poll

    return () => clearInterval(interval);
  }, []);

  // Listen for live socket updates
  useEffect(() => {
    socket.on('new_log', (log) => {
      // Increment real-time EPS counter
      logCounterRef.current += 1;

      setLogs((prev) => {
        const exists = prev.some(l => l.timestamp === log.timestamp && l.raw === log.raw);
        if (exists) return prev;
        return [log, ...prev].slice(0, 50);
      });
    });

    socket.on('new_alert', (alert) => {
      setAlerts((prev) => {
        const exists = prev.some(a => a.timestamp === alert.timestamp && a.alert_title === alert.alert_title);
        if (exists) return prev;
        return [alert, ...prev];
      });
    });

    // Real-time SOAR active defense blockers
    socket.on('ip_blocked', (data) => {
      setBlockedIps((prev) => {
        if (prev.some(item => item.ip === data.ip)) return prev;
        return [...prev, data];
      });
    });

    socket.on('ip_unblocked', (data) => {
      setBlockedIps((prev) => prev.filter(item => item.ip !== data.ip));
    });

    return () => {
      socket.off('new_log');
      socket.off('new_alert');
      socket.off('ip_blocked');
      socket.off('ip_unblocked');
    };
  }, []);

  // Send Manual Unblock requests to the SOAR API
  const handleUnblock = (ip) => {
    fetch(`http://${hostname}:5000/api/soar/unblock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ip })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        setBlockedIps(prev => prev.filter(item => item.ip !== ip));
      }
    })
    .catch(err => console.error("Error unblocking IP:", err));
  };

  // Filter logs based on search query
  const filteredLogs = logs.filter(log => {
    const query = searchQuery.toLowerCase();
    return (
      log.raw?.toLowerCase().includes(query) ||
      log.event_type?.toLowerCase().includes(query) ||
      log.source_ip?.toLowerCase().includes(query) ||
      log.agent_host?.toLowerCase().includes(query) ||
      (log.user_name && log.user_name.toLowerCase().includes(query))
    );
  });

  // Calculate unique hosts/devices sending data
  const uniqueHosts = new Set(logs.map(l => l.agent_host || 'localhost')).size;

  // Calculate Notice vs Warning syslog alerts matching the Log360 layout
  const noticeCount = logs.filter(l => l.severity === 'info' || l.severity === 'low').length;
  const warningCount = logs.filter(l => l.severity === 'critical' || l.severity === 'high' || l.severity === 'medium').length;

  return (
    <div>
      {/* Top Navbar Menu */}
      <nav className="top-nav">
        <div className="brand-logo-container">
          <span className="brand-logo-text">
            NEXUS-<span className="brand-logo-highlight">SIEM</span>
          </span>
        </div>
        <div className="nav-menu">
          <a href="#" className="nav-menu-item active">Dashboard</a>
        </div>
      </nav>

      {/* Main Dashboard Container */}
      <div className="dashboard-container" style={{ marginTop: '1rem' }}>
        
        {/* KPI metrics row */}
        <div className="kpi-row">
          {/* Card 1: Ingest Volatility / EPS Sparkline */}
          <div className="kpi-card">
            <div className="kpi-left" style={{ width: '65%' }}>
              <span className="kpi-title">Ingest Volatility</span>
              <span className="kpi-value">{epsVal} <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-secondary)' }}>EPS</span></span>
              <span className="kpi-trend trend-up">
                ▲ {trendGrowth}
              </span>
            </div>
            <div className="kpi-sparkline-container" style={{ width: '35%', height: '40px', alignSelf: 'center' }}>
              <EPSSparkline data={epsHistory} />
            </div>
          </div>

          {/* Card 2: Syslog Events */}
          <div className="kpi-card">
            <div className="kpi-left">
              <span className="kpi-title">Syslog Events</span>
              <span className="kpi-value">{logs.length}</span>
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', marginTop: '0.25rem', fontWeight: 500 }}>
                <span style={{ color: 'var(--accent-green)' }}>● Notice {noticeCount}</span>
                <span style={{ color: 'var(--accent-red)' }}>● Warning {warningCount}</span>
              </div>
            </div>
            <div style={{ fontSize: '1.5rem', opacity: 0.2 }}>🐧</div>
          </div>

          {/* Card 3: All Devices */}
          <div className="kpi-card">
            <div className="kpi-left">
              <span className="kpi-title">Monitored Devices</span>
              <span className="kpi-value">{uniqueHosts}</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--accent-green)', fontWeight: 600 }}>
                Online & Active
              </span>
            </div>
            <div className="kpi-right">
              <div className="device-indicator">
                <span className="device-dot"></span>
                ACTIVE
              </div>
              <div style={{ fontSize: '1.3rem', opacity: 0.2 }}>🖥️</div>
            </div>
          </div>
        </div>

        {/* Row 1: Map and Charts side-by-side */}
        <div className="dashboard-grid-middle">
          {/* Left: Attacker Geo-Mapping World Map */}
          <ThreatMap blockedIps={blockedIps} />
          
          {/* Right: Stacked charts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <LogsTrendChart logs={logs} />
            <div className="split-charts-row">
              <TopDevicesChart logs={logs} />
              <SeverityDonutChart logs={logs} />
            </div>
          </div>
        </div>

        {/* Row 2: Live Ingest, Alerts, and SOAR Blocker */}
        <div className="dashboard-grid-bottom">
          {/* Column 1: Live Ingest logs table card */}
          <div className="card">
            <div className="table-controls">
              <h3 className="card-title" style={{ fontSize: '0.8rem' }}>Live Ingest Stream</h3>
              <input
                type="text"
                placeholder="Search raw logs..."
                className="search-box"
                style={{ width: '160px', padding: '0.35rem 0.6rem', fontSize: '0.75rem' }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <LiveLogTable logs={filteredLogs} />
          </div>

          {/* Column 2: Recent Alerts Feed */}
          <AlertCard alerts={alerts} />

          {/* Column 3: SOAR Active Defense Blocker Card */}
          <div className="card">
            <div className="card-header-bar">
              <h3 className="card-title" style={{ fontSize: '0.8rem' }}>SOAR Active Defense</h3>
              <span className="device-indicator" style={{ backgroundColor: 'rgba(239, 68, 68, 0.08)', borderColor: 'rgba(239, 68, 68, 0.2)', color: 'var(--accent-red)' }}>
                <span className="device-dot" style={{ backgroundColor: 'var(--accent-red)' }}></span>
                {blockedIps.length} BLOCKED
              </span>
            </div>
            <div className="alerts-feed-container">
              {blockedIps.length === 0 ? (
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                  Firewall secure. No active blocks.
                </div>
              ) : (
                blockedIps.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0.6rem', border: '1px solid var(--border-color)', borderRadius: '4px', backgroundColor: '#fcfcfe', marginBottom: '0.4rem', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'monospace', color: '#1a202c' }}>{item.ip}</span>
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }} title={item.reason}>
                        {item.reason?.substring(0, 18)}...
                      </span>
                    </div>
                    <button 
                      onClick={() => handleUnblock(item.ip)}
                      style={{ padding: '0.2rem 0.4rem', fontSize: '0.65rem', fontWeight: 600, border: '1px solid var(--accent-blue)', color: 'var(--accent-blue)', backgroundColor: 'transparent', borderRadius: '4px', cursor: 'pointer', transition: 'all 0.2s' }}
                      onMouseOver={(e) => { e.target.style.backgroundColor = 'var(--accent-blue)'; e.target.style.color = '#fff'; }}
                      onMouseOut={(e) => { e.target.style.backgroundColor = 'transparent'; e.target.style.color = 'var(--accent-blue)'; }}
                    >
                      Unblock
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}