// Reusable UI component to display streaming live log table
import React from 'react';

export default function LiveLogTable({ logs }) {
  const getSeverityStyleClass = (type) => {
    if (type === 'failed_login') return 'severity-critical severity-indicator';
    if (type === 'http_404') return 'severity-high severity-indicator';
    if (type === 'successful_login' || type?.startsWith('http_200') || type === 'cron_job') return 'severity-info severity-indicator';
    return 'severity-indicator';
  };

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Agent Host</th>
            <th>Event Type</th>
            <th>Source IP</th>
            <th>Target User</th>
            <th>Raw Payload</th>
          </tr>
        </thead>
        <tbody>
          {logs.length === 0 ? (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2.5rem', fontSize: '0.82rem' }}>
                Awaiting telemetry logs... Start agent service or traffic simulator.
              </td>
            </tr>
          ) : (
            logs.map((log, i) => (
              <tr key={i}>
                <td className="mono" style={{ whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                  {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '-'}
                </td>
                <td className="mono">{log.agent_host || 'localhost'}</td>
                <td className={getSeverityStyleClass(log.event_type)}>
                  {log.event_type}
                </td>
                <td className="mono">{log.source_ip || '-'}</td>
                <td className="mono" style={{ color: log.user_name ? 'var(--accent-blue)' : 'inherit', fontWeight: log.user_name ? 600 : 'normal' }}>
                  {log.user_name || '-'}
                </td>
                <td className="mono" style={{ opacity: 0.85, maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.raw}>
                  {log.raw}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
