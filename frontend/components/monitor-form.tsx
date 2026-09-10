'use client';

import { FormEvent, useState } from 'react';
import { Loader2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getApiErrorMessage } from '@/lib/api';

export type MonitorFormValues = {
  url: string;
  http_method: string;
  expected_status_code: number;
  interval_seconds: number;
  timeout_seconds: number;
  failure_threshold: number;
  recovery_threshold: number;
  notification_webhook_url: string;
};

type MonitorFormProps = {
  initialValues?: Partial<MonitorFormValues>;
  submitLabel: string;
  title: string;
  onSubmit: (values: MonitorFormValues) => Promise<void>;
  onClose: () => void;
};

const defaults: MonitorFormValues = {
  url: '',
  http_method: 'GET',
  expected_status_code: 200,
  interval_seconds: 60,
  timeout_seconds: 10,
  failure_threshold: 2,
  recovery_threshold: 2,
  notification_webhook_url: '',
};

export function MonitorForm({ initialValues, submitLabel, title, onSubmit, onClose }: MonitorFormProps) {
  const [values, setValues] = useState<MonitorFormValues>({ ...defaults, ...initialValues });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (field: keyof MonitorFormValues, value: string) => {
    setValues((current) => ({
      ...current,
      [field]: field === 'url' || field === 'http_method' || field === 'notification_webhook_url' ? value : Number(value),
    }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      const url = new URL(values.url);
      if (!['http:', 'https:'].includes(url.protocol)) throw new Error('URL must use http or https.');
      if (values.interval_seconds < 10) throw new Error('Check interval must be at least 10 seconds.');
      if (values.timeout_seconds < 1) throw new Error('Timeout must be at least 1 second.');
      if (values.expected_status_code < 100 || values.expected_status_code > 599) {
        throw new Error('Expected status must be between 100 and 599.');
      }
      setSubmitting(true);
      await onSubmit(values);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : getApiErrorMessage(submitError, 'The API rejected this monitor. Check the values and try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  const fields: Array<{ field: keyof MonitorFormValues; label: string; type?: string; min?: number; max?: number }> = [
    { field: 'expected_status_code', label: 'Expected status', min: 100, max: 599 },
    { field: 'interval_seconds', label: 'Check interval (seconds)', min: 10 },
    { field: 'timeout_seconds', label: 'Timeout (seconds)', min: 1 },
    { field: 'failure_threshold', label: 'Failures before incident', min: 1, max: 10 },
    { field: 'recovery_threshold', label: 'Successes before recovery', min: 1, max: 10 },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm">
      <Card className="max-h-[90vh] w-full max-w-2xl overflow-y-auto border-slate-700 bg-slate-900 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-xl text-white">{title}</CardTitle>
          <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close form">
            <X className="h-5 w-5" />
          </Button>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={submit}>
            <label className="block space-y-2 text-sm text-slate-300">
              URL
              <input
                required
                type="url"
                value={values.url}
                onChange={(event) => update('url', event.target.value)}
                placeholder="https://api.example.com/health"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block space-y-2 text-sm text-slate-300">
                HTTP method
                <select
                  value={values.http_method}
                  onChange={(event) => update('http_method', event.target.value)}
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
                >
                  {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'].map((method) => (
                    <option key={method}>{method}</option>
                  ))}
                </select>
              </label>
              {fields.slice(0, 1).map(({ field, label, min, max }) => (
                <NumberField key={field} field={field} label={label} value={values[field] as number} min={min} max={max} onChange={update} />
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {fields.slice(1).map(({ field, label, min, max }) => (
                <NumberField key={field} field={field} label={label} value={values[field] as number} min={min} max={max} onChange={update} />
              ))}
            </div>
            <label className="block space-y-2 text-sm text-slate-300">
              Notification webhook (optional)
              <input
                type="url"
                value={values.notification_webhook_url}
                onChange={(event) => update('notification_webhook_url', event.target.value)}
                placeholder="https://hooks.example.com/nexus"
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
              />
            </label>
            {error ? <p className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</p> : null}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={onClose} className="border-slate-700 text-slate-200">
                Cancel
              </Button>
              <Button type="submit" disabled={submitting} className="gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {submitting ? 'Saving…' : submitLabel}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function NumberField({
  field,
  label,
  value,
  min,
  max,
  onChange,
}: {
  field: keyof MonitorFormValues;
  label: string;
  value: number;
  min?: number;
  max?: number;
  onChange: (field: keyof MonitorFormValues, value: string) => void;
}) {
  return (
    <label className="block space-y-2 text-sm text-slate-300">
      {label}
      <input
        required
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(field, event.target.value)}
        className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-cyan-400"
      />
    </label>
  );
}
