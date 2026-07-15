import React from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  BarChart, Bar
} from 'recharts';

// 1. Logs Trend Area Chart
export function LogsTrendChart({ logs }) {
  // Aggregate logs count by seconds/minutes
  const timeBuckets = {};
  
  // Sort logs chronologically to aggregate
  [...logs].reverse().forEach(log => {
    if (!log.timestamp) return;
    const timeStr = new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    timeBuckets[timeStr] = (timeBuckets[timeStr] || 0) + 1;
  });

  const data = Object.keys(timeBuckets).map(time => ({
    time,
    count: timeBuckets[time]
  })).slice(-10); // Display the latest 10 data points

  // Fill in mock points if data is empty to prevent blank charts
  if (data.length === 0) {
    for (let i = 9; i >= 0; i--) {
      const dummyTime = new Date(Date.now() - i * 5000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      data.push({ time: dummyTime, count: 0 });
    }
  }

  return (
    <div className="card">
      <div className="card-header-bar">
        <h3 className="card-title">Logs Trend</h3>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Event Count / Time</span>
      </div>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" stroke="#a0aec0" fontSize={10} tickLine={false} />
            <YAxis stroke="#a0aec0" fontSize={10} tickLine={false} />
            <Tooltip contentStyle={{ fontSize: '11px', fontFamily: 'sans-serif' }} />
            <Area type="monotone" dataKey="count" stroke="var(--accent-blue)" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// 2. Top 5 Devices Pie Chart
export function TopDevicesChart({ logs }) {
  // Aggregate log counts by source_ip or agent_host
  const deviceCounts = {};
  
  logs.forEach(log => {
    const host = log.source_ip || log.agent_host || '127.0.0.1';
    deviceCounts[host] = (deviceCounts[host] || 0) + 1;
  });

  const rawData = Object.keys(deviceCounts).map(host => ({
    name: host,
    value: deviceCounts[host]
  }));

  // Sort and take top 5
  const data = rawData.sort((a, b) => b.value - a.value).slice(0, 5);

  const COLORS = ['#0070f3', '#10b981', '#f97316', '#a855f7', '#06b6d4'];

  return (
    <div className="card">
      <div className="card-header-bar">
        <h3 className="card-title">Top Devices</h3>
      </div>
      <div style={{ width: '100%', height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {data.length === 0 ? (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>No device data</span>
        ) : (
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={55}
                paddingAngle={3}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [`${value} logs`]} contentStyle={{ fontSize: '10px' }} />
              <Legend verticalAlign="bottom" height={36} iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

// 3. Syslog Severity Bar Chart
export function SeverityChart({ logs }) {
  const severities = {
    Info: 0,
    Low: 0,
    Medium: 0,
    High: 0,
    Critical: 0
  };

  logs.forEach(log => {
    const sev = log.severity?.toUpperCase() || 'INFO';
    if (sev === 'CRITICAL') severities.Critical += 1;
    else if (sev === 'HIGH') severities.High += 1;
    else if (sev === 'MEDIUM') severities.Medium += 1;
    else if (sev === 'LOW') severities.Low += 1;
    else severities.Info += 1;
  });

  const data = [
    { name: 'Info', count: severities.Info, fill: '#10b981' },
    { name: 'Low', count: severities.Low, fill: '#3b82f6' },
    { name: 'Medium', count: severities.Medium, fill: '#eab308' },
    { name: 'High', count: severities.High, fill: '#f97316' },
    { name: 'Critical', count: severities.Critical, fill: '#ef4444' }
  ];

  return (
    <div className="card">
      <div className="card-header-bar">
        <h3 className="card-title">Events by Severity</h3>
      </div>
      <div style={{ width: '100%', height: 180 }}>
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 10, right: 10, left: -30, bottom: 0 }}>
            <XAxis dataKey="name" stroke="#a0aec0" fontSize={9} tickLine={false} />
            <YAxis stroke="#a0aec0" fontSize={9} tickLine={false} />
            <Tooltip cursor={{ fill: 'rgba(0,0,0,0.02)' }} contentStyle={{ fontSize: '10px' }} />
            <Bar dataKey="count" radius={[2, 2, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
