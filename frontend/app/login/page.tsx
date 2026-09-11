'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { Loader2, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
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

export function AuthCard(props: {
  title: string;
  subtitle: string;
  email: string;
  password: string;
  setEmail: (value: string) => void;
  setPassword: (value: string) => void;
  error: string | null;
  loading: boolean;
  submit: (event: FormEvent) => void;
  action: string;
  footer: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-md space-y-8 rounded-2xl border border-slate-800 bg-slate-900/70 p-8 shadow-2xl">
        <div className="text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-violet-500 text-slate-950"><Sparkles className="h-6 w-6" /></div>
          <h1 className="mt-5 text-2xl font-semibold text-white">{props.title}</h1>
          <p className="mt-2 text-sm text-slate-400">{props.subtitle}</p>
        </div>
        <form className="space-y-5" onSubmit={props.submit}>
          <label className="block space-y-2 text-sm text-slate-300">Email<input required type="email" value={props.email} onChange={(event) => props.setEmail(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" /></label>
          <label className="block space-y-2 text-sm text-slate-300">Password<input required minLength={8} type="password" value={props.password} onChange={(event) => props.setPassword(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-white" /></label>
          {props.error ? <p className="rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{props.error}</p> : null}
          <Button disabled={props.loading} className="w-full gap-2 bg-cyan-500 text-slate-950 hover:bg-cyan-400">{props.loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{props.loading ? 'Working…' : props.action}</Button>
        </form>
        <div className="text-center">{props.footer}</div>
      </div>
    </main>
  );
}
