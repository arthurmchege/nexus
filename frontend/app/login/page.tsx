'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthCard } from '@/components/auth-card';
import { apiFetch, getApiResponseErrorMessage } from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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

  return <AuthCard title="Welcome back" subtitle="Sign in to your NEXUS workspace" email={email} password={password} setEmail={setEmail} setPassword={setPassword} error={error} loading={loading} submit={submit} action="Sign in" footer={<p className="text-sm text-slate-400">New to NEXUS? <Link className="text-cyan-300 hover:text-cyan-200" href="/signup">Create an account</Link></p>} />;
}
