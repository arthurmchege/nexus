'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, ChevronRight, LayoutGrid, ShieldCheck, Sparkles } from 'lucide-react';

import { cn } from '@/lib/utils';

const navItems = [
  { href: '/', label: 'Overview', icon: LayoutGrid },
  { href: '/monitors', label: 'Monitors', icon: Activity },
  { href: '#', label: 'Alerts', icon: ShieldCheck },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <div className="mx-auto flex min-h-screen max-w-[1600px]">
        <aside className="hidden w-72 shrink-0 border-r border-slate-800 bg-slate-950/80 p-6 md:block">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-violet-500 text-slate-950 shadow-glow">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Platform</p>
              <h1 className="text-xl font-semibold text-white">NEXUS</h1>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ href, label, icon: Icon }) => {
              const isActive = href !== '#' && pathname === href;
              const isPlaceholder = href === '#';

              return (
                <Link
                  key={label}
                  href={href}
                  className={cn(
                    'flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm transition-colors',
                    isPlaceholder
                      ? 'cursor-not-allowed border-slate-800 bg-slate-900/50 text-slate-500'
                      : isActive
                        ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200'
                        : 'border-transparent bg-slate-900/30 text-slate-300 hover:border-slate-700 hover:bg-slate-900/80',
                  )}
                  aria-disabled={isPlaceholder}
                >
                  <span className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    {label}
                  </span>
                  {!isPlaceholder ? <ChevronRight className="h-4 w-4" /> : null}
                </Link>
              );
            })}
          </nav>

          <div className="mt-10 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2 text-sm text-emerald-300">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              System online
            </div>
            <p className="mt-2 text-xs text-slate-400">Monitoring runtime stable and collecting data.</p>
          </div>
        </aside>

        <main className="flex-1">
          <header className="border-b border-slate-800 bg-slate-950/80 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 md:hidden">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-violet-500 text-slate-950">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-white">NEXUS</p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm text-slate-300">
                <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(74,222,128,0.8)]" />
                Live status
              </div>
            </div>
          </header>

          <div className="px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
