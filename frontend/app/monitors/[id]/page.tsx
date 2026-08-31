'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Gauge, RefreshCcw, ServerCog, TimerReset } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { StatusBadge } from '@/components/monitor-status';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui-states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';

type MonitorDetail = {
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

type StatsPayload = {
  monitor_id: number;
  window_start: string;
  window_end: string;
  total_checks: number;
  successful_checks: number;
  failed_checks: number;
  uptime_percentage: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  hourly_rollups: Array<{
    bucket: string;
    total_checks: number;
    successful_checks: number;
    failed_checks: number;
    uptime_percentage: number;
    avg_latency_ms: number;
  }>;
  daily_rollups: Array<{
    bucket: string;
    total_checks: number;
    successful_checks: number;
    failed_checks: number;
    uptime_percentage: number;
    avg_latency_ms: number;
  }>;
};

type HistoryItem = {
  id: number;
  endpoint_id: number;
  observed_at: string;
  http_status: number;
  latency_ms: number;
  response_size: number;
  success: boolean;
  error_category?: string | null;
  error_details?: string | null;
};

export default function MonitorDetailPage() {
  const params = useParams<{ id: string }>();
  const monitorId = Number(params.id);

  const [monitor, setMonitor] = useState<MonitorDetail | null>(null);
  const [stats, setStats] = useState<StatsPayload | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historySkip, setHistorySkip] = useState(0);
  const [limit] = useState(8);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(monitorId)) {
      setError('Invalid monitor ID.');
      setLoading(false);
      return;
    }

    const fetchMonitor = async () => {
      try {
        setLoading(true);
        setError(null);

        const [monitorRes, statsRes, historyRes] = await Promise.all([
          fetch(`${apiBase}/api/v1/monitors/${monitorId}`),
          fetch(`${apiBase}/api/v1/monitors/${monitorId}/stats?window_days=30`),
          fetch(`${apiBase}/api/v1/monitors/${monitorId}/history?skip=${historySkip}&limit=${limit}`),
        ]);

        if (!monitorRes.ok || !statsRes.ok || !historyRes.ok) {
          throw new Error('This monitor could not be loaded.');
        }

        const monitorData = (await monitorRes.json()) as MonitorDetail;
        const statsData = (await statsRes.json()) as StatsPayload;
        const historyData = (await historyRes.json()) as HistoryItem[];

        setMonitor(monitorData);
        setStats(statsData);
        setHistory(historyData);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    void fetchMonitor();
  }, [monitorId, historySkip, limit]);

  const latencySeries = useMemo(
    () =>
      (stats?.hourly_rollups ?? []).map((point) => ({
        label: point.bucket,
        latency: Number(point.avg_latency_ms ?? 0),
      })),
    [stats],
  );

  const uptimeSeries = useMemo(
    () =>
      (stats?.hourly_rollups ?? []).map((point) => ({
        label: point.bucket,
        uptime: Number(point.uptime_percentage ?? 0),
      })),
    [stats],
  );

  if (loading) {
    return <LoadingCards count={4} />;
  }

  if (error) {
    return <ErrorState title="Monitor detail unavailable" description={error} onRetry={() => window.location.reload()} />;
  }

  if (!monitor || !stats) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <Link href="/monitors" className="inline-flex items-center gap-2 text-slate-300 hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Back to monitors
          </Link>
        </div>
        <Button variant="outline" className="gap-2 border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800" onClick={() => window.location.reload()}>
          <RefreshCcw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Card className="border-slate-800 bg-slate-900/70 panel-glow">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Monitor</p>
            <CardTitle className="mt-2 text-2xl text-white">{monitor.url}</CardTitle>
            <p className="mt-2 text-sm text-slate-400">
              {monitor.http_method} · expected {monitor.expected_status_code} · interval {monitor.interval_seconds}s
            </p>
          </div>
          <StatusBadge status={monitor.status ?? 'unknown'} />
        </CardHeader>
      </Card>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Uptime', value: `${stats.uptime_percentage.toFixed(2)}%`, icon: Gauge },
          { label: 'P50 latency', value: `${Math.round(stats.p50_latency_ms)} ms`, icon: TimerReset },
          { label: 'P95 latency', value: `${Math.round(stats.p95_latency_ms)} ms`, icon: ServerCog },
          { label: 'Checks', value: `${stats.total_checks}`, icon: RefreshCcw },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label} className="border-slate-800 bg-slate-900/70 panel-glow">
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div>
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 text-cyan-300">
                <Icon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card className="border-slate-800 bg-slate-900/70 panel-glow">
          <CardHeader>
            <CardTitle className="text-white">Latency over time</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {latencySeries.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={latencySeries}>
                  <defs>
                    <linearGradient id="latencyFill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.5} />
                      <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 12 }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Area type="monotone" dataKey="latency" stroke="#22d3ee" strokeWidth={2} fill="url(#latencyFill)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="No latency data" description="No checks have been recorded for this monitor in the selected window." />
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-900/70 panel-glow">
          <CardHeader>
            <CardTitle className="text-white">Uptime trend</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {uptimeSeries.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={uptimeSeries}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: 12 }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Line type="monotone" dataKey="uptime" stroke="#34d399" strokeWidth={2.5} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="No uptime data" description="This monitor does not have any completed checks yet." />
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="border-slate-800 bg-slate-900/70 panel-glow">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">History</p>
            <CardTitle className="mt-2 text-xl text-white">Recent checks</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800" disabled={historySkip === 0} onClick={() => setHistorySkip((current) => Math.max(0, current - limit))}>
              Previous
            </Button>
            <Button variant="outline" className="border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800" disabled={history.length < limit} onClick={() => setHistorySkip((current) => current + limit)}>
              Next
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <EmptyState title="No check history" description="This endpoint has not recorded any completed checks in the current slice." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Observed</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Latency</TableHead>
                  <TableHead>Response</TableHead>
                  <TableHead>Size</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-slate-300">
                      {new Date(item.observed_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </TableCell>
                    <TableCell>
                      <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${item.success ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>
                        {item.success ? 'Success' : 'Failure'}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-300">{item.latency_ms} ms</TableCell>
                    <TableCell className="text-slate-300">{item.http_status}</TableCell>
                    <TableCell className="text-slate-300">{item.response_size} B</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
