import React, { useState } from 'react';

// Robinson projection tables (latitude steps of 5 degrees)
const robinsonAA = [
  0.8487, 0.8475, 0.8448, 0.8402, 0.8336, 0.8258, 0.8148, 0.8001, 0.7822, 
  0.7606, 0.7366, 0.7087, 0.6778, 0.6448, 0.6099, 0.5713, 0.5273, 0.4856, 0.4517
];
const robinsonBB = [
  0.0000, 0.0838, 0.1677, 0.2515, 0.3354, 0.4192, 0.5031, 0.5869, 0.6705, 
  0.7534, 0.8352, 0.9154, 0.9934, 1.0687, 1.1407, 1.2084, 1.2704, 1.3200, 1.3523
];

// Translate lat/lon coordinates into percentage values within the map viewBox
function projectCoordinates(lat, lon) {
  // Handle empty or invalid coords
  if (lat === undefined || lon === undefined || isNaN(lat) || isNaN(lon)) {
    return { x: 50, y: 50 }; // Default to center
  }

  const latitudeAbs = Math.abs(lat);
  const latitudeStepFloor = Math.floor(latitudeAbs / 5);
  const latitudeStepCeil = Math.min(Math.ceil(latitudeAbs / 5), 18);
  const latitudeInterpolation = (latitudeAbs - latitudeStepFloor * 5) / 5;
  
  // Interpolate AA and BB constants
  const AA = robinsonAA[latitudeStepFloor] + (robinsonAA[latitudeStepCeil] - robinsonAA[latitudeStepFloor]) * latitudeInterpolation;
  const BB = robinsonBB[latitudeStepFloor] + (robinsonBB[latitudeStepCeil] - robinsonBB[latitudeStepFloor]) * latitudeInterpolation;
  
  // SVG original dimensions
  const mapWidth = 784.077;
  const robinsonWidth = 2 * Math.PI * robinsonAA[0];
  const widthFactor = mapWidth / robinsonWidth;
  
  // Robinson projection equations
  const x = (widthFactor * AA * lon * Math.PI) / 180;
  const y = widthFactor * BB * Math.sign(lat);
  
  // Calibrated projection offset matching the downloaded SVG viewBox coordinates
  // viewBox="30.767 241.591 784.077 458.627"
  const centerX = 30.767 + 784.077 / 2; // 422.8055
  const centerY = 526.646; // Calibrated Equator line
  
  const targetX = centerX + x;
  const targetY = centerY - y;
  
  // Map coordinates to percentage positions relative to top-left of the viewBox
  const pctX = ((targetX - 30.767) / 784.077) * 100;
  const pctY = ((targetY - 241.591) / 458.627) * 100;
  
  // Clamp boundaries to prevent coordinate leak outside SVG container
  return { 
    x: Math.max(0, Math.min(100, pctX)), 
    y: Math.max(0, Math.min(100, pctY)) 
  };
}

export default function ThreatMap({ blockedIps = [] }) {
  const [hoveredIp, setHoveredIp] = useState(null);

  // Group blocked IPs that might have the exact same coordinates/mock-location
  const ipMap = {};
  blockedIps.forEach(item => {
    if (!item.location) return;
    const key = `${item.location.lat.toFixed(2)}_${item.location.lon.toFixed(2)}`;
    if (!ipMap[key]) {
      ipMap[key] = [];
    }
    ipMap[key].push(item);
  });

  return (
    <div className="threat-map-card">
      <div className="threat-map-title">
        <span>Attacker Geo-Mapping (Active Firewall Blocks)</span>
        <span style={{ fontSize: '0.7rem', color: '#ffca28', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-red)', display: 'inline-block' }}></span>
          LIVE RADAR
        </span>
      </div>

      <div className="threat-map-container">
        {/* World Map Background Asset */}
        <object 
          type="image/svg+xml" 
          data="/world-map.svg" 
          className="map-svg-background"
          aria-label="World Map"
        />

        {/* Legend Overlay */}
        <div className="map-legend">
          <div className="map-legend-item">
            <span className="map-legend-dot" style={{ backgroundColor: 'var(--accent-red)' }}></span>
            <span>Blocked Attacker IP</span>
          </div>
          <div className="map-legend-item">
            <span className="map-legend-dot" style={{ backgroundColor: '#ffca28' }}></span>
            <span>Simulated Subnet</span>
          </div>
        </div>

        {/* Threat marker overlays */}
        {Object.keys(ipMap).map((key, index) => {
          const items = ipMap[key];
          const primaryItem = items[0];
          const { lat, lon } = primaryItem.location;
          const { x, y } = projectCoordinates(lat, lon);

          const isGroup = items.length > 1;

          return (
            <div 
              key={index}
              className="threat-marker"
              style={{ left: `${x}%`, top: `${y}%` }}
              onMouseEnter={() => setHoveredIp(primaryItem.ip)}
              onMouseLeave={() => setHoveredIp(null)}
            >
              <div 
                className="threat-dot" 
                style={{ 
                  backgroundColor: primaryItem.location.type === 'private' ? '#ffca28' : 'var(--accent-red)',
                  boxShadow: primaryItem.location.type === 'private' ? '0 0 10px #ffca28' : '0 0 10px var(--accent-red)'
                }}
              />
              <div 
                className="threat-pulse" 
                style={{ 
                  borderColor: primaryItem.location.type === 'private' ? '#ffca28' : 'var(--accent-red)'
                }}
              />

              {/* Hover Tooltip inside marker container for absolute position relative to dot */}
              {hoveredIp === primaryItem.ip && (
                <div className="map-tooltip">
                  <div className="map-tooltip-header">
                    ⚔️ {isGroup ? `${items.length} IPs Blocked` : `Blocked IP: ${primaryItem.ip}`}
                  </div>
                  <div className="map-tooltip-body">
                    <div><strong>City/Country:</strong> {primaryItem.location.city}, {primaryItem.location.country}</div>
                    <div><strong>Coordinates:</strong> {lat.toFixed(3)}°N, {lon.toFixed(3)}°E</div>
                    {isGroup ? (
                      <div className="map-tooltip-reason">
                        IPs: {items.map(i => i.ip).join(', ')}
                      </div>
                    ) : (
                      <>
                        <div><strong>Reason:</strong> {primaryItem.reason}</div>
                        <div className="map-tooltip-reason">
                          Blocked: {new Date(primaryItem.blocked_at).toLocaleTimeString()}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
