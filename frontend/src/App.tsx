import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

type Summary = { device_count: number; temperature: number; humidity: number; air_quality: number; alert_count: number; updated_at: string | null };
type Reading = { timestamp: string; temperature: number; humidity: number; air_quality: number; alert_status?: string };
type Device = { device_id: string; timestamp?: string; status?: string; temperature?: number; humidity?: number; alert_status?: string };
const API = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export default function App() {
  const [summary, setSummary] = useState<Summary>();
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [history, setHistory] = useState<Reading[]>([]);
  const [alerts, setAlerts] = useState<Reading[]>([]);
  const [error, setError] = useState('');
  const [updated, setUpdated] = useState('');

  useEffect(() => {
    let active = true;
    const loadOverview = async () => {
      try {
        const [summaryResponse, devicesResponse, alertsResponse] = await Promise.all([
          fetch(API + '/api/v1/analytics/summary'),
          fetch(API + '/api/v1/devices'),
          fetch(API + '/api/v1/alerts?limit=8'),
        ]);
        if (![summaryResponse, devicesResponse, alertsResponse].every((response) => response.ok)) {
          throw new Error('API request failed');
        }
        const [nextSummary, nextDevices, nextAlerts] = await Promise.all([
          summaryResponse.json(), devicesResponse.json(), alertsResponse.json(),
        ]);
        if (active) {
          setSummary(nextSummary);
          setDevices(nextDevices.items || []);
          setAlerts(nextAlerts.items || []);
          setSelectedDevice((current) => current || nextDevices.items?.[0]?.device_id || '');
          setError('');
          setUpdated(new Date().toLocaleTimeString());
        }
      } catch {
        if (active) setError('Could not reach the monitoring API. Check the API URL and CORS settings.');
      }
    };
    loadOverview();
    const timer = window.setInterval(loadOverview, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (!selectedDevice) return;
    let active = true;
    const loadHistory = async () => {
      try {
        const response = await fetch(API + '/api/v1/devices/' + encodeURIComponent(selectedDevice) + '/telemetry?limit=48');
        if (!response.ok) throw new Error('History request failed');
        const result = await response.json();
        if (active) setHistory(result.items || []);
      } catch {
        if (active) setError('Could not load device history.');
      }
    };
    loadHistory();
    const timer = window.setInterval(loadHistory, 15000);
    return () => { active = false; window.clearInterval(timer); };
  }, [selectedDevice]);

  const sourceLabel = API.includes('localhost') ? 'Local API' : 'Cloud API';
  return <main>
    <header>
      <div><div className="eyebrow">SMART HOME / ENVIRONMENT</div><h1>Home Monitor</h1><p>Environmental conditions across your connected home</p></div>
      <div className="headerTools">
        <label className="deviceSelect">Device
          <select value={selectedDevice} onChange={(event) => setSelectedDevice(event.target.value)}>
            {devices.length === 0 && <option value="">Waiting for devices</option>}
            {devices.map((device) => <option key={device.device_id} value={device.device_id}>{device.device_id}</option>)}
          </select>
        </label>
        <div className="pill"><i /> {sourceLabel}</div>
      </div>
    </header>
    {error && <div className="error">{error}</div>}
    <section className="cards">
      {[
        ['Temperature', summary ? summary.temperature + '°C' : '—', 'Current device average'],
        ['Humidity', summary ? summary.humidity + '%' : '—', 'Current device average'],
        ['Air quality', summary?.air_quality ?? '—', 'Sensor index'],
        ['Active devices', summary?.device_count ?? '—', 'Reporting sensors'],
        ['Open alerts', summary?.alert_count ?? '—', 'Warning or critical'],
      ].map(([label, value, hint]) => <article className="card" key={label}><span>{label}</span><strong>{value}</strong><small>{hint}</small></article>)}
    </section>
    <section className="panel">
      <div className="panelHead"><div><h2>Environmental trends</h2><p>{selectedDevice || 'Select a device'} · recent sensor readings</p></div><span className="live" aria-label="Automatically refreshes every 15 seconds"><i /> POLLING · 15S</span></div>
      <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history}>
        <defs><linearGradient id="temp" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4cc9aa" stopOpacity={.3}/><stop offset="95%" stopColor="#4cc9aa" stopOpacity={0}/></linearGradient></defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#263542"/>
        <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} stroke="#8091a1"/>
        <YAxis stroke="#8091a1"/><Tooltip contentStyle={{ background: '#14232d', border: '1px solid #30414d' }}/>
        <Area type="monotone" dataKey="temperature" name="Temperature °C" stroke="#4cc9aa" fill="url(#temp)"/>
        <Area type="monotone" dataKey="humidity" name="Humidity %" stroke="#75a8e8" fill="transparent"/>
      </AreaChart></ResponsiveContainer></div>
    </section>
    <section className="panel alertPanel">
      <div className="panelHead"><div><h2>Recent alerts</h2><p>Threshold events from sensor telemetry</p></div><span className="count">{alerts.length} shown</span></div>
      {alerts.length ? <div className="alertList">{alerts.map((alert, index) => <div className="alertRow" key={alert.timestamp + index}><span className={'alertMark ' + (alert.alert_status || 'warning')}/><div><strong>{alert.alert_status || 'Warning'}</strong><small>{alert.timestamp} · {alert.temperature}°C · {alert.humidity}% humidity</small></div><span className="alertValue">{alert.temperature}°C</span></div>)}</div> : <div className="emptyState">No active threshold alerts.</div>}
    </section>
    <footer>Last refreshed {updated || '—'} · API data source: {sourceLabel}</footer>
  </main>;
}
