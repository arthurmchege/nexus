'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { AlertTriangle, BellRing, CheckCircle2, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui-states';

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8001';

type Delivery = {
  id: number;
  event: string;
  channel: string;
  status: string;
  attempts: number;
  last_error?: string | null;
  delivered_at?: string | null;
};

type Incident = {
  id: number;
  monitor_id: number;
  opened_at: string;
  resolved_at?: string | null;
  trigger_reason: string;
  status: 'open' | 'resolved';
  deliveries: Delivery[];
};

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString() : '—';
}

export default function AlertsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${apiBase}/api/v1/alerts?limit=100`);
      if (!response.ok) {
        throw new Error('The alert history is unavailable right now.');
      }
      setIncidents((await response.json()) as Incident[]);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAlerts();
  }, []);

  if (loading) {
    return <LoadingCards count={3} />;
  }

  if (error) {
    return <ErrorState title="Alerts unavailable" description={error} onRetry={() => void loadAlerts()} />;
  }

  const openIncidents = incidents.filter((incident) => incident.status === 'open');
  const resolvedIncidents = incidents.filter((incident) => incident.status === 'resolved');

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Alerts</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Incident center</h2>
          <p className="mt-2 text-sm text-slate-400">State changes, recovery events, and notification delivery.</p>
        </div>
        <Button
          variant="outline"
          className="gap-2 border-slate-700 bg-slate-900 text-slate-100 hover:bg-slate-800"
          onClick={() => void loadAlerts()}
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {incidents.length === 0 ? (
        <Card className="border-slate-800 bg-slate-900/70 panel-glow">
          <CardContent className="pt-6">
            <EmptyState
              title="No incidents recorded"
              description="NEXUS will show an incident here after a monitor crosses its configured failure threshold."
              action={
                <Link href="/monitors">
                  <Button className="bg-cyan-500 text-slate-950 hover:bg-cyan-400">View monitors</Button>
                </Link>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            <Card className="border-red-500/20 bg-red-500/5 panel-glow">
              <CardContent className="flex items-center gap-4 p-5">
                <AlertTriangle className="h-6 w-6 text-red-300" />
                <div>
                  <p className="text-sm text-slate-400">Open incidents</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{openIncidents.length}</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-emerald-500/20 bg-emerald-500/5 panel-glow">
              <CardContent className="flex items-center gap-4 p-5">
                <CheckCircle2 className="h-6 w-6 text-emerald-300" />
                <div>
                  <p className="text-sm text-slate-400">Resolved incidents</p>
                  <p className="mt-1 text-2xl font-semibold text-white">{resolvedIncidents.length}</p>
                </div>
              </CardContent>
            </Card>
          </section>

          <Card className="border-slate-800 bg-slate-900/70 panel-glow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <BellRing className="h-5 w-5 text-cyan-300" />
                Incident history
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {incidents.map((incident) => (
                <div key={incident.id} className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="font-medium text-white">
                        Monitor #{incident.monitor_id} · {incident.status === 'open' ? 'Open' : 'Resolved'}
                      </p>
                      <p className="mt-1 text-sm text-slate-400">{incident.trigger_reason}</p>
                      <p className="mt-2 text-xs text-slate-500">
                        Opened {formatDate(incident.opened_at)} · Resolved {formatDate(incident.resolved_at)}
                      </p>
                    </div>
                    <div className="space-y-2 text-left lg:text-right">
                      {incident.deliveries.map((delivery) => (
                        <p key={delivery.id} className="text-xs text-slate-400">
                          {delivery.event} · {delivery.channel} ·{' '}
                          <span className={delivery.status === 'delivered' ? 'text-emerald-300' : 'text-amber-300'}>
                            {delivery.status}
                          </span>{' '}
                          ({delivery.attempts} attempt{delivery.attempts === 1 ? '' : 's'})
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
