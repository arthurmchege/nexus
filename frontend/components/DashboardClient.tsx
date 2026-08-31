'use client';

import { useEffect, useState } from 'react';

type DashboardSummary = {
  total_monitors: number;
  down_monitors: number;
  overall_uptime_percentage: number;
  window_start: string;
  window_end: string;
};

export function DashboardClient() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';
    if (typeof fetch !== 'function') {
      return;
    }

    fetch(`${apiBase}/api/v1/monitors/summary`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`request failed with status ${response.status}`);
        }
        return response.json();
      })
      .then((data: DashboardSummary) => setSummary(data))
      .catch((fetchError: Error) => setError(fetchError.message));
  }, []);

  return (
    <section style={{ marginTop: '1.5rem', display: 'grid', gap: '1rem' }}>
      <h2>Monitoring Overview</h2>
      {error ? <p>API unavailable: {error}</p> : null}
      {summary ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
          <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: '1rem' }}>
            <div style={{ color: '#666' }}>Total monitors</div>
            <strong>{summary.total_monitors}</strong>
          </div>
          <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: '1rem' }}>
            <div style={{ color: '#666' }}>Down monitors</div>
            <strong>{summary.down_monitors}</strong>
          </div>
          <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: '1rem' }}>
            <div style={{ color: '#666' }}>Overall uptime</div>
            <strong>{summary.overall_uptime_percentage.toFixed(2)}%</strong>
          </div>
          <div style={{ border: '1px solid #ddd', borderRadius: 8, padding: '1rem' }}>
            <div style={{ color: '#666' }}>Window</div>
            <small>{summary.window_start} → {summary.window_end}</small>
          </div>
        </div>
      ) : (
        <p>Loading monitoring summary…</p>
      )}
    </section>
  );
}
