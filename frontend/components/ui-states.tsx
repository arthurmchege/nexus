import { AlertTriangle, Inbox, RefreshCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function LoadingCards({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="border-slate-800 bg-slate-900/70">
          <CardContent className="p-5">
            <Skeleton className="mb-4 h-4 w-24 bg-slate-800" />
            <Skeleton className="h-8 w-16 bg-slate-800" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function ErrorState({ title, description, onRetry }: { title?: string; description?: string; onRetry?: () => void }) {
  return (
    <Card className="border-red-500/30 bg-slate-900/70">
      <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 text-red-400">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-white">{title ?? 'Unable to load data'}</h3>
          <p className="max-w-md text-sm text-slate-300">
            {description ?? 'The API is currently unavailable or returned an unexpected response.'}
          </p>
        </div>
        {onRetry ? (
          <Button variant="outline" onClick={onRetry} className="gap-2 border-slate-700 text-slate-100 hover:bg-slate-800">
            <RefreshCcw className="h-4 w-4" />
            Retry
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <Card className="border-dashed border-slate-700 bg-slate-900/60">
      <CardContent className="flex flex-col items-center justify-center gap-4 py-16 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-800 text-slate-300">
          <Inbox className="h-7 w-7" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-white">{title}</h3>
          <p className="max-w-lg text-sm text-slate-300">{description}</p>
        </div>
        {action}
      </CardContent>
    </Card>
  );
}
