// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

const responses: Record<string, unknown> = {
  '/api/v1/analytics/summary': {
    device_count: 1, registered_device_count: 1, temperature: 24, humidity: 45,
    air_quality: 90, alert_count: 0, updated_at: '2026-11-01T10:00:00Z',
  },
  '/api/v1/devices?limit=200': {
    items: [{ device_id: 'sensor-1', status: 'online', timestamp: '2026-11-01T10:00:00Z', temperature: 24, humidity: 45 }],
  },
  '/api/v1/alerts?limit=8': { items: [] },
  '/api/v1/devices/sensor-1/telemetry?limit=48': { items: [] },
};

function mockFetch() {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input));
    const body = responses[url.pathname + url.search];
    if (!body) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => body };
  }));
}

describe('monitoring dashboard', () => {
  beforeEach(() => mockFetch());
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('loads the overview and states its polling interval', async () => {
    render(<App />);
    expect(await screen.findByText('Home Monitor')).toBeTruthy();
    expect(await screen.findByText('24°C')).toBeTruthy();
    expect(screen.getByText('Auto refresh · 15 sec')).toBeTruthy();
    expect(screen.queryByText('LIVE')).toBeNull();
  });

  it('shows the fleet and opens device analytics', async () => {
    render(<App />);
    await screen.findByText('Home Monitor');
    fireEvent.click(screen.getByRole('button', { name: 'Device fleet' }));
    expect(await screen.findByText('Last reading: 2026-11-01T10:00:00Z')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /sensor-1/ }));
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Selected device' })).toBeTruthy());
  });

  it('explains that the security event feed is unavailable', async () => {
    render(<App />);
    await screen.findByText('Home Monitor');
    fireEvent.click(screen.getByRole('button', { name: 'Security center' }));
    expect(await screen.findByText('Security event feed is not configured')).toBeTruthy();
  });
});
