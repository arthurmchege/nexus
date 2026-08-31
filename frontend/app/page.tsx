'use client';

import { Activity, ArrowRight, CheckCircle2, Clock3, Gauge, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState, ErrorState, LoadingCards } from '@/components/ui-states';

const stats = [
  { label: 'Total monitors', value: '0', accent: 'text-cyan-300', icon: Activity },
  { label: 'Down monitors', value: '0', accent: 'text-red-400', icon: ShieldAlert },
  { label: 'Overall uptime', value: '0.00%', accent: 'text-emerald-300', icon: Gauge },
  { label: 'Monitoring window', value: '30d', accent: 'text-violet-300', icon: Clock3 },
];

export default function HomePage() {
  const isLoading = false;
  const error = null;

  if (error) {
    return <ErrorState title="Overview unavailable" description={error} onRetry={() => window.location.reload()} />;
  }

  if (isLoading) {
    return <LoadingCards count={4} />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">Overview</p>
          <h2 className="mt-2 text-3xl font-semibold text-white">Operations snapshot</h2>
        </div>
        <Badge variant="success" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-300">
          <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
          Healthy
        </Badge>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map(({ label, value, accent, icon: Icon }) => (
          <Card key={label} className="border-slate-800 bg-slate-900/70">
            <CardContent className="flex items-center justify-between gap-4 p-5">
              <div>
                <p className="text-sm text-slate-400">{label}</p>
                <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
              </div>
              <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-slate-800 ${accent}`}>
                <Icon className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <Card className="border-slate-800 bg-slate-900/70">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Status</p>
            <CardTitle className="mt-2 text-xl text-white">No monitors configured</CardTitle>
          </div>
          <Button variant="outline" className="border-slate-700 bg-slate-950 text-slate-100 hover:bg-slate-800">
            Refresh data
          </Button>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="No monitors are being tracked yet"
            description="Create a monitor through the API, then the dashboard will surface health, latency, and incident trends here."
            action={
              <Button className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">
                Add monitor via API
                <ArrowRight className="h-4 w-4" />
              </Button>
            }
          />
        </CardContent>
      </Card>
    </div>
  );
}
