'use client';

import { usePathname } from 'next/navigation';

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/engines': 'Scraping Engines',
  '/engines/create': 'Create Engine',
  '/jobs': 'Scraped Jobs',
  '/settings': 'Settings',
};

export default function Header() {
  const pathname = usePathname();
  const title = PAGE_TITLES[pathname] || 'Job Scrapper';

  return (
    <header className="header">
      <h2 className="header-title">{title}</h2>
      <div className="header-actions">
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          AI-Powered Job Scraper
        </span>
      </div>
    </header>
  );
}
