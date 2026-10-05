import type { ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <Sidebar />
      <div className="shell__main">
        <Topbar />
        <main className="page">{children}</main>
      </div>
    </div>
  );
}
