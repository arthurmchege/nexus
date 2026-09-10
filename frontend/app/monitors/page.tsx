'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight, Globe, Pause, Play, Plus, RefreshCw, Trash2 } from 'lucide-react';

import { MonitorForm, type MonitorFormValues } from '@/components/monitor-form';
import { StatusBadge } from '@/components/monitor-status';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui-states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

import { buildApiUrl, getApiErrorMessage } from '@/lib/api';

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';

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

export default function MonitorListPage() {
  const [monitors, setMonitors] = useState<MonitorRecord[]>([]);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionId, setActionId] = useState<number | null>(null);

  useEffect(() => {
    const fetchMonitors = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${apiBase}/api/v1/monitors?skip=${skip}&limit=${limit}`);
        if (!response.ok) {
          throw new Error('The monitor list is unavailable right now.');
        }

        const payload = (await response.json()) as MonitorRecord[];
        setMonitors(payload);
      } catch (fetchError) {
        setError(fetchError instanceof Error ? fetchError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    void fetchMonitors();
  }, [skip, limit]);

  const createMonitor = async (values: MonitorFormValues) => {
    const response = await fetch(buildApiUrl('/api/v1/monitors'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...values, notification_webhook_url: values.notification_webhook_url || null }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(getApiErrorMessage(payload, 'The monitor could not be created.'));
    }
    const created = (await response.json()) as MonitorRecord;
    setMonitors((current) => [created, ...current]);
    setShowCreate(false);
    setNotice('Monitor created successfully.');
  };

  const toggleMonitor = async (monitor: MonitorRecord) => {
    setActionId(monitor.id);
    try {
      const response = await fetch(buildApiUrl(`/api/v1/monitors/${monitor.id}/${monitor.active ? 'deactivate' : 'activate'}`), { method: 'POST' });
      if (!response.ok) throw new Error(getApiErrorMessage(await response.json().catch(() => null), 'The monitor status could not be changed.'));
      setMonitors((current) => current.map((item) => (item.id === monitor.id ? { ...item, active: !monitor.active } : item)));
      setNotice(`Monitor ${monitor.active ? 'paused' : 'resumed'}.`);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'The monitor status could not be changed.');
    } finally {
      setActionId(null);
    }
  };

  const deleteMonitor = async (monitor: MonitorRecord) => {
    if (!window.confirm(`Delete ${monitor.url}? This cannot be undone.`)) return;
    setActionId(monitor.id);
    try {
      const response = await fetch(buildApiUrl(`/api/v1/monitors/${monitor.id}`), { method: 'DELETE' });
      if (!response.ok) throw new Error(getApiErrorMessage(await response.json().catch(() => null), 'The monitor could not be deleted.'));
      setMonitors((current) => current.filter((item) => item.id !== monitor.id));
      setNotice('Monitor deleted.');
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : 'The monitor could not be deleted.');
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return <LoadingCards count={4} />;
  }

  if (error) {
    return <ErrorState title="Monitor list unavailable" description={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Monitors</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Endpoint inventory</h2>
        </div>
        <div className="flex gap-2">
          <Button className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400" onClick={() => setShowCreate(true)}>
            <Plus className="h-4 w-4" />
            Add monitor
          </Button>
          <Button variant="outline" className="gap-2 border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800" onClick={() => setSkip(0)}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>
      {notice ? <p className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">{notice}</p> : null}

      <Card className="border-slate-800 bg-slate-900/70 panel-glow">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Overview</p>
            <CardTitle className="mt-2 text-xl text-white">All monitored endpoints</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" className="gap-2 border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800" disabled={skip === 0} onClick={() => setSkip((current) => Math.max(0, current - limit))}>
              <ChevronLeft className="h-4 w-4" />
              Prev
            </Button>
            <Button variant="outline" className="gap-2 border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800" disabled={monitors.length < limit} onClick={() => setSkip((current) => current + limit)}>
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {monitors.length === 0 ? (
            <EmptyState
              title="No monitors detected"
              description="Create your first endpoint to start collecting health, latency, and incident data."
              action={<Button className="bg-cyan-500 text-slate-950 hover:bg-cyan-400" onClick={() => setShowCreate(true)}>Add your first monitor</Button>}
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Monitor</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Method</TableHead>
                  <TableHead>Interval</TableHead>
                  <TableHead>Last update</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {monitors.map((monitor) => (
                  <TableRow key={monitor.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-300">
                          <Globe className="h-4 w-4" />
                        </div>
                        <div>
                          <p className="font-medium text-white">{monitor.url}</p>
                          <p className="text-xs text-slate-400">HTTP {monitor.expected_status_code}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={monitor.status ?? 'unknown'} />
                    </TableCell>
                    <TableCell>
                      <span className="rounded border border-slate-700 bg-slate-800 px-2 py-1 text-xs uppercase tracking-[0.2em] text-slate-300">
                        {monitor.http_method}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-300">{monitor.interval_seconds}s</TableCell>
                    <TableCell className="text-slate-300">
                      {new Date(monitor.updated_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={actionId === monitor.id}
                          onClick={() => void toggleMonitor(monitor)}
                          className="gap-1 text-slate-300 hover:text-white"
                        >
                          {monitor.active ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
                          {monitor.active ? 'Pause' : 'Resume'}
                        </Button>
                        <Button variant="ghost" size="icon" disabled={actionId === monitor.id} onClick={() => void deleteMonitor(monitor)} aria-label={`Delete ${monitor.url}`} className="text-red-400 hover:bg-red-500/10 hover:text-red-300">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        <Link href={`/monitors/${monitor.id}`} className="inline-flex items-center gap-2 text-cyan-300 hover:text-cyan-200">
                          View
                          <ArrowRight className="h-4 w-4" />
                        </Link>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {showCreate ? (
        <MonitorForm title="Add monitor" submitLabel="Create monitor" onSubmit={createMonitor} onClose={() => setShowCreate(false)} />
      ) : null}
    </div>
  );
}
