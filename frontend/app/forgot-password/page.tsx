'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { AuthCard } from '@/components/auth-card';
import { apiFetch, getApiResponseErrorMessage } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    const response = await apiFetch('/api/v1/auth/request-password-reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) setError(getApiResponseErrorMessage(response, payload, 'Unable to request a reset link.'));
    else setMessage(payload?.message ?? 'If an account exists, a reset link has been sent.');
    setLoading(false);
  }

  return <AuthCard title="Reset your password" subtitle="Recover your NEXUS workspace" email={email} password="" setEmail={setEmail} setPassword={() => undefined} showPassword={false} error={error} loading={loading} submit={submit} action="Send reset link" footer={<p className="text-sm text-slate-400">{message ?? <>Remembered it? <Link className="text-cyan-300 hover:text-cyan-200" href="/login">Back to sign in</Link></>}</p>} />;
}
