'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Activity, ArrowRight, Clock3, Gauge, ShieldAlert } from 'lucide-react';

import { StatusBadge } from '@/components/monitor-status';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui-states';

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';

type DashboardSummary = {
  total_monitors: number;
  down_monitors: number;
  overall_uptime_percentage: number;
  window_start: string;
  window_end: string;
};

type MonitorRecord = {
  id: number;
  url: string;
  http_method: string;
  expected_status_code: number;
  interval_seconds: number;
  timeout_seconds: number;
  active: boolean;
  created_at: string;
  updated_at: string;
  status?: string;
};

function formatWindowRange(start: string, end: string) {
  const format = (value: string) => new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  return `${format(start)} → ${format(end)}`;
}

export default function HomePage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [monitors, setMonitors] = useState<MonitorRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        setLoading(true);
        setError(null);

        const [summaryRes, monitorsRes] = await Promise.all([
          fetch(`${apiBase}/api/v1/monitors/summary`),
          fetch(`${apiBase}/api/v1/monitors?skip=0&limit=5`),
        ]);

        if (!summaryRes.ok || !monitorsRes.ok) {
          throw new Error('The API is unavailable right now.');
        }

        const summaryData = (await summaryRes.json()) as DashboardSummary;
        const monitoringData = (await monitorsRes.json()) as MonitorRecord[];

        setSummary(summaryData);
        setMonitors(monitoringData);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    void fetchOverview();
  }, []);

  if (loading) {
    return <LoadingCards count={4} />;
  }

  if (error) {
    return <ErrorState title="Overview unavailable" description={error} onRetry={() => window.location.reload()} />;
  }

  if (!summary) {
    return null;
  }

  const statCards = [
    { label: 'Total monitors', value: summary.total_monitors, accent: 'text-cyan-300', icon: Activity },
    { label: 'Down monitors', value: summary.down_monitors, accent: 'text-red-400', icon: ShieldAlert },
    { label: 'Overall uptime', value: `${summary.overall_uptime_percentage.toFixed(2)}%`, accent: 'text-emerald-300', icon: Gauge },
    { label: 'Monitoring window', value: formatWindowRange(summary.window_start, summary.window_end), accent: 'text-violet-300', icon: Clock3 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Overview</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Operations snapshot</h2>
        </div>
        <Button variant="outline" className="border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800" onClick={() => window.location.reload()}>
          Refresh data
        </Button>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map(({ label, value, accent, icon: Icon }) => (
          <Card key={label} className="border-slate-800 bg-slate-900/70 panel-glow">
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div>
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-3 text-xl font-semibold text-white sm:text-2xl">{value}</p>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 ${accent}`}>
                <Icon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <Card className="border-slate-800 bg-slate-900/70 panel-glow">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Live queue</p>
            <CardTitle className="mt-2 text-xl text-white">
              {summary.total_monitors === 0 ? 'No monitors configured' : 'Tracked monitors'}
            </CardTitle>
          </div>
          <Link href="/monitors">
            <Button variant="outline" className="border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800">
              View all
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {summary.total_monitors === 0 ? (
            <EmptyState
              title="No monitors are being tracked yet"
              description="Create a monitor through the API, then the dashboard will surface health, latency, and incident trends here."
              action={
                <Link href="/monitors">
                  <Button className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">
                    Browse monitors
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="space-y-3">
              {monitors.map((monitor) => (
                <Link
                  key={monitor.id}
                  href={`/monitors/${monitor.id}`}
                  className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/50 p-4 transition-colors hover:border-slate-700 hover:bg-slate-950"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{monitor.url}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {monitor.http_method} · {monitor.interval_seconds}s interval · {monitor.active ? 'Active' : 'Inactive'}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusBadge status={monitor.status ?? 'unknown'} />
                    <ArrowRight className="h-4 w-4 text-slate-500" />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
