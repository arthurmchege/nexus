import { Activity, AlertTriangle, CheckCircle2, CircleDashed } from 'lucide-react';

import { Badge } from '@/components/ui/badge';

export type MonitorStatus = 'up' | 'down' | 'unknown' | 'degraded';

export function getMonitorStatusVariant(status?: string): 'success' | 'destructive' | 'outline' | 'warning' {
  switch (status?.toLowerCase()) {
    case 'up':
      return 'success';
    case 'down':
      return 'destructive';
    case 'degraded':
      return 'warning';
    default:
      return 'outline';
  }
}

export function getMonitorStatusLabel(status?: string) {
  switch (status?.toLowerCase()) {
    case 'up':
      return 'Up';
    case 'down':
      return 'Down';
    case 'degraded':
      return 'Degraded';
    default:
      return 'Unknown';
  }
}

export function StatusBadge({ status }: { status?: string }) {
  const variant = getMonitorStatusVariant(status);

  const Icon =
    variant === 'success'
      ? CheckCircle2
      : variant === 'destructive'
        ? AlertTriangle
        : variant === 'warning'
          ? Activity
          : CircleDashed;

  return (
    <Badge variant={variant} className="gap-1.5 px-2.5 py-1">
      <Icon className="h-3.5 w-3.5" />
      {getMonitorStatusLabel(status)}
    </Badge>
  );
}
