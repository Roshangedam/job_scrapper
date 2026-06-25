'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_ITEMS = [
  { href: '/', icon: '📊', label: 'Dashboard' },
  { href: '/engines', icon: '⚙️', label: 'Engines' },
  { href: '/jobs', icon: '💼', label: 'Scraped Jobs' },
];

const NAV_SETTINGS = [
  { href: '/settings', icon: '🔧', label: 'Settings' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🔍</div>
        <h1>Job Scrapper</h1>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Main</div>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}

        <div className="nav-section-label">Configuration</div>
        {NAV_SETTINGS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </aside>
  );
}
