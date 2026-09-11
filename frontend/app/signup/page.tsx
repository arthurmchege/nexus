'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthCard } from '@/app/login/page';
import { apiFetch, getApiResponseErrorMessage } from '@/lib/api';

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const response = await apiFetch('/api/v1/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      setError(getApiResponseErrorMessage(response, await response.json().catch(() => null), 'The account could not be created.'));
      setLoading(false);
      return;
    }
    window.location.href = '/';
  }

  return <AuthCard title="Create your workspace" subtitle="Start monitoring with NEXUS" email={email} password={password} setEmail={setEmail} setPassword={setPassword} error={error} loading={loading} submit={submit} action="Create account" footer={<p className="text-sm text-slate-400">Already registered? <Link className="text-cyan-300 hover:text-cyan-200" href="/login">Sign in</Link></p>} />;
}
