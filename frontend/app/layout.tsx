import './globals.css';
import type { Metadata } from 'next';

import { DashboardShell } from '@/components/dashboard-shell';

export const metadata: Metadata = {
  title: 'NEXUS',
  description: 'Developer operations platform for API health and reliability',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-slate-950 text-slate-50 antialiased">
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
