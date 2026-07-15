// Reusable UI component to display recent security alerts in a sidebar feed
import React from 'react';

export default function AlertCard({ alerts }) {
  const getSeverityClass = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'strip-critical';
      case 'HIGH': return 'strip-high';
      case 'MEDIUM': return 'strip-medium';
      case 'LOW': return 'strip-low';
      default: return 'strip-info';
    }
  };

  return (
    <div className="card" style={{ padding: '1rem' }}>
      <div className="card-header-bar" style={{ marginBottom: '1rem' }}>
        <h3 className="card-title" style={{ fontSize: '0.8rem' }}>Recent Alerts</h3>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Live Feed</span>
      </div>
      
      <div className="alerts-feed-container">
        {alerts.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            No alerts triggered. System is monitoring logs.
          </div>
        ) : (
          alerts.map((a, i) => (
            <div key={i} className="alert-card-item">
              {/* Vertical Color Strip depending on severity */}
              <div className={`alert-severity-strip ${getSeverityClass(a.severity)}`} />
              
              <div className="alert-content-box">
                <div className="alert-item-header">
                  <span className="alert-item-title">{a.alert_title}</span>
                  <span className="alert-item-time">
                    {a.timestamp ? new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                  </span>
                </div>
                <div className="alert-item-details">
                  Source: <span style={{ fontFamily: 'monospace', fontWeight: 500, color: 'var(--text-primary)' }}>{a.source_ip || 'localhost'}</span>
                </div>
                <div className="alert-item-header" style={{ marginTop: '0.2rem' }}>
                  <span className="alert-item-hits">
                    Events: <span style={{ fontFamily: 'monospace' }}>{a.trigger_count || 1}</span>
                  </span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                    {a.severity || 'info'}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
