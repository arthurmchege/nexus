'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthCard } from '@/components/auth-card';
import { Button } from '@/components/ui/button';
import { apiFetch, getApiResponseErrorMessage } from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const response = await apiFetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError(getApiResponseErrorMessage(response, await response.json().catch(() => null), 'Invalid email or password.'));
      setLoading(false);
      return;
    }
    window.location.href = '/';
  }

  async function viewDemo() {
    setDemoLoading(true);
    setError(null);
    const response = await apiFetch('/api/v1/auth/demo-login', { method: 'POST' });
    if (!response.ok) {
      setError(getApiResponseErrorMessage(response, await response.json().catch(() => null), 'The demo is unavailable right now.'));
      setDemoLoading(false);
      return;
    }
    window.location.href = '/';
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to your NEXUS workspace"
      email={email}
      password={password}
      setEmail={setEmail}
      setPassword={setPassword}
      error={error}
      loading={loading || demoLoading}
      submit={submit}
      action="Sign in"
      footer={
        <div className="space-y-3">
          <Button type="button" variant="outline" disabled={loading || demoLoading} onClick={() => void viewDemo()} className="w-full border-cyan-500/40 text-cyan-200 hover:bg-cyan-500/10">
            {demoLoading ? 'Opening demo…' : 'View public demo'}
          </Button>
          <p className="text-sm text-slate-400">New to NEXUS? <Link className="text-cyan-300 hover:text-cyan-200" href="/signup">Create an account</Link></p>
        </div>
      }
    />
  );
}
