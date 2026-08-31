import { DashboardClient } from '@/components/DashboardClient';

export default function HomePage() {
  return (
    <main style={{ padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1>NEXUS</h1>
      <p>Developer operations platform foundation</p>
      <DashboardClient />
    </main>
  );
}
