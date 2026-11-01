import { useEffect, useState } from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

type View = 'overview' | 'fleet' | 'analytics' | 'alerts' | 'security';
type Summary = {
  device_count: number;
  registered_device_count?: number;
  temperature: number;
  humidity: number;
  air_quality: number;
  alert_count: number;
  updated_at: string | null;
};
type Reading = {
  timestamp: string;
  device_id?: string;
  temperature: number;
  humidity: number;
  air_quality: number;
  alert_status?: string;
  event_id?: string;
};
type Device = {
  device_id: string;
  timestamp?: string;
  latest?: string;
  last_status_at?: string;
  status?: string;
  temperature?: number;
  humidity?: number;
  air_quality?: number;
  alert_status?: string;
};

const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
const NAV: { id: View; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'fleet', label: 'Device fleet' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'security', label: 'Security center' },
];

async function fetchJson(path: string) {
  const response = await fetch(API + path);
  if (!response.ok) throw new Error('API request failed');
  return response.json();
}

export default function App() {
  const [view, setView] = useState<View>('overview');
  const [summary, setSummary] = useState<Summary>();
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [history, setHistory] = useState<Reading[]>([]);
  const [historyLimit, setHistoryLimit] = useState(48);
  const [alerts, setAlerts] = useState<Reading[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [updated, setUpdated] = useState('');

  useEffect(() => {
    let active = true;
    const loadOverview = async () => {
      try {
        const [nextSummary, nextDevices, nextAlerts] = await Promise.all([
          fetchJson('/api/v1/analytics/summary'),
          fetchJson('/api/v1/devices?limit=200'),
          fetchJson('/api/v1/alerts?limit=8'),
        ]);
        if (!active) return;
        setSummary(nextSummary);
        setDevices(nextDevices.items || []);
        setAlerts(nextAlerts.items || []);
        setSelectedDevice((current) => current || nextDevices.items?.[0]?.device_id || '');
        setError('');
        setLoading(false);
        setUpdated(new Date().toLocaleTimeString());
      } catch {
        if (active) {
          setError('Could not reach the monitoring API. Check the API URL and CORS settings.');
          setLoading(false);
        }
      }
    };
    void loadOverview();
    const timer = window.setInterval(loadOverview, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (!selectedDevice) {
      setHistory([]);
      return;
    }
    let active = true;
    const loadHistory = async () => {
      try {
        const result = await fetchJson(
          '/api/v1/devices/' + encodeURIComponent(selectedDevice) + '/telemetry?limit=' + historyLimit,
        );
        if (active) setHistory(result.items || []);
      } catch {
        if (active) setError('Could not load device history.');
      }
    };
    void loadHistory();
    const timer = window.setInterval(loadHistory, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [selectedDevice, historyLimit]);

  const sourceLabel = API.includes('localhost') ? 'Local demo' : 'AWS API';
  const connectionLabel = error ? 'Unavailable' : 'Connected';

  const metricCards = [
    ['Online devices', summary?.device_count ?? '—', 'Currently reporting'],
    ['Registered devices', summary?.registered_device_count ?? devices.length, 'In this home'],
    ['Avg. temperature', summary ? summary.temperature + '°C' : '—', 'Latest device readings'],
    ['Avg. humidity', summary ? summary.humidity + '%' : '—', 'Latest device readings'],
    ['Open alerts', summary?.alert_count ?? '—', 'Warning or critical'],
  ];

  const chart = <section className="panel">
    <div className="panelHead">
      <div><h2>Environmental trends</h2><p>{selectedDevice || 'Select a device'} · recent sensor readings</p></div>
      <label className="rangeSelect">Readings
        <select value={historyLimit} onChange={(event) => setHistoryLimit(Number(event.target.value))}>
          <option value={24}>24</option><option value={48}>48</option><option value={96}>96</option>
        </select>
      </label>
    </div>
    {history.length ? <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history}>
      <defs><linearGradient id="temp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4cc9aa" stopOpacity={.3}/><stop offset="95%" stopColor="#4cc9aa" stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid strokeDasharray="3 3" stroke="#263542"/>
      <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} stroke="#8091a1"/>
      <YAxis stroke="#8091a1"/><Tooltip contentStyle={{ background: '#14232d', border: '1px solid #30414d' }}/>
      <Area type="monotone" dataKey="temperature" name="Temperature °C" stroke="#4cc9aa" fill="url(#temp)"/>
      <Area type="monotone" dataKey="humidity" name="Humidity %" stroke="#75a8e8" fill="transparent"/>
    </AreaChart></ResponsiveContainer></div> : <div className="emptyState">{loading ? 'Loading telemetry…' : 'No readings are available for this device yet.'}</div>}
  </section>;

  const alertPanel = <section className="panel alertPanel">
    <div className="panelHead"><div><h2>Recent alerts</h2><p>Threshold events from sensor telemetry</p></div><span className="count">{alerts.length} shown</span></div>
    {alerts.length ? <div className="alertList">{alerts.map((alert, index) =>
      <div className="alertRow" key={alert.event_id || alert.timestamp + index}>
        <span className={'alertMark ' + (alert.alert_status || 'warning')}/>
        <div><strong>{alert.alert_status || 'Warning'}</strong><small>{alert.device_id || 'Device'} · {alert.timestamp} · {alert.temperature}°C · {alert.humidity}% humidity</small></div>
        <span className="alertValue">{alert.temperature}°C</span>
      </div>,
    )}</div> : <div className="emptyState">{loading ? 'Loading alerts…' : 'No threshold alerts have been reported.'}</div>}
  </section>;

  return <main>
    <header>
      <div><div className="eyebrow">SMART HOME / ENVIRONMENT</div><h1>Home Monitor</h1><p>Environmental conditions across your connected home</p></div>
      <div className="headerTools">
        <label className="deviceSelect">Selected device
          <select value={selectedDevice} onChange={(event) => setSelectedDevice(event.target.value)}>
            {devices.length === 0 && <option value="">Waiting for devices</option>}
            {devices.map((device) => <option key={device.device_id} value={device.device_id}>{device.device_id}</option>)}
          </select>
        </label>
        <div className="pill"><i className={error ? 'offline' : ''}/> {sourceLabel} · {connectionLabel}</div>
      </div>
    </header>

    <nav className="viewTabs" aria-label="Monitoring views">
      {NAV.map((item) => <button
        type="button"
        key={item.id}
        aria-current={view === item.id ? 'page' : undefined}
        className={view === item.id ? 'active' : ''}
        onClick={() => setView(item.id)}
      >{item.label}</button>)}
      <span className="pollNote">Auto refresh · 15 sec</span>
    </nav>

    {error && <div className="error" role="alert">{error}</div>}
    {loading && <div className="loadingNote" role="status">Connecting to {sourceLabel.toLowerCase()}…</div>}

    {view === 'overview' && <>
      <section className="cards" aria-label="Home summary">
        {metricCards.map(([label, value, hint]) => <article className="card" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>)}
      </section>
      {chart}
      {alertPanel}
    </>}

    {view === 'fleet' && <section className="panel">
      <div className="panelHead"><div><h2>Device fleet</h2><p>{devices.length} devices returned by the configured home</p></div></div>
      {devices.length ? <div className="fleetList">{devices.map((device) =>
        <button type="button" className="fleetRow" key={device.device_id} onClick={() => { setSelectedDevice(device.device_id); setView('analytics'); }}>
          <span className={'deviceStatus ' + (device.status === 'online' ? 'online' : 'offline')}/>
          <span className="fleetIdentity"><strong>{device.device_id}</strong><small>Last reading: {device.timestamp || device.latest || 'No reading timestamp'}</small></span>
          <span className="fleetMetric">{device.temperature ?? '—'}°C</span>
          <span className="fleetMetric">{device.humidity ?? '—'}% RH</span>
          <span className="fleetState">{device.status || 'unknown'}</span>
        </button>,
      )}</div> : <div className="emptyState">{loading ? 'Loading registered devices…' : 'No devices are registered in this home.'}</div>}
    </section>}

    {view === 'analytics' && <>{chart}<section className="panel">
      <div className="panelHead"><div><h2>Selected device</h2><p>{selectedDevice || 'No device selected'}</p></div></div>
      {selectedDevice && <div className="detailMetrics">
        <span><small>Temperature</small><strong>{history[history.length - 1]?.temperature ?? '—'}°C</strong></span>
        <span><small>Humidity</small><strong>{history[history.length - 1]?.humidity ?? '—'}%</strong></span>
        <span><small>Air quality index</small><strong>{history[history.length - 1]?.air_quality ?? '—'}</strong></span>
        <span><small>Latest sample</small><strong>{history[history.length - 1]?.timestamp ? new Date(history[history.length - 1].timestamp).toLocaleString() : '—'}</strong></span>
      </div>}
    </section></>}

    {view === 'alerts' && alertPanel}

    {view === 'security' && <section className="panel securityPanel">
      <div className="panelHead"><div><h2>Security center</h2><p>Device identity and suspicious-activity monitoring</p></div><span className="count">Not connected</span></div>
      <div className="securityNotice">
        <strong>Security event feed is not configured</strong>
        <p>This deployment does not yet publish certificate lifecycle, authorization failures, or suspicious-telemetry events to the dashboard. Device certificates must be managed in AWS IoT and reviewed in CloudWatch.</p>
      </div>
      <div className="securityGrid">
        <article><small>Certificate status</small><strong>Unavailable</strong><span>No certificate inventory API</span></article>
        <article><small>Suspicious telemetry</small><strong>Unavailable</strong><span>Anomaly detection is not enabled</span></article>
        <article><small>Connectivity anomalies</small><strong>Unavailable</strong><span>Historical presence analysis is not enabled</span></article>
      </div>
    </section>}

    <footer>Last successful refresh {updated || '—'} · Source: {sourceLabel} · Dashboard data is polled every 15 seconds</footer>
  </main>;
}
