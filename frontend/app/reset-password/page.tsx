'use client';

import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { FormEvent, useState } from 'react';

import { AuthCard } from '@/components/auth-card';
import { apiFetch, getApiResponseErrorMessage } from '@/lib/api';

export default function ResetPasswordPage() {
  const token = useSearchParams().get('token') ?? '';
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(token ? null : 'This reset link is missing its token.');
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const response = await apiFetch('/api/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) setError(getApiResponseErrorMessage(response, payload, 'The reset link is invalid or expired.'));
    else {
      setError(null);
      setMessage(payload?.message ?? 'Password reset successfully.');
    }
  }

  return <AuthCard title="Choose a new password" subtitle="Your reset link expires after 15 minutes" email="" password={password} setEmail={() => undefined} setPassword={setPassword} showEmail={false} error={error} loading={false} submit={submit} action="Reset password" footer={<p className="text-sm text-slate-400">{message ? <><span>{message} </span><Link className="text-cyan-300 hover:text-cyan-200" href="/login">Sign in</Link></> : 'Use at least 8 characters.'}</p>} />;
}
