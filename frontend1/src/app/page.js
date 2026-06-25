'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import Link from 'next/link';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [statsData, healthData] = await Promise.all([
        api.getDashboardStats(),
        api.getScrapeHealth(),
      ]);
      setStats(statsData);
      setHealth(healthData);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div className="loading-spinner"></div>;

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Overview of your job scraping activity</p>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">⚙️</div>
          <div className="stat-value">{stats?.active_engines || 0}</div>
          <div className="stat-label">Active Engines</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💼</div>
          <div className="stat-value">{stats?.total_jobs || 0}</div>
          <div className="stat-label">Total Jobs Found</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-value">{stats?.jobs_today || 0}</div>
          <div className="stat-label">Jobs Today</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-value">{stats?.average_match_pct || 0}%</div>
          <div className="stat-label">Avg Match Score</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🏆</div>
          <div className="stat-value">{stats?.high_match_count || 0}</div>
          <div className="stat-label">High Match Jobs (75%+)</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '28px' }}>
        <Link href="/engines/create" className="btn btn-primary">
          ➕ Create Engine
        </Link>
        <Link href="/jobs" className="btn btn-secondary">
          💼 View All Jobs
        </Link>
      </div>

      {/* Scrape Health */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h3 className="card-title">🩺 Scrape Health Monitor</h3>
        </div>

        {health?.platform_stats?.length > 0 ? (
          <div className="health-grid">
            {health.platform_stats.map((p) => (
              <div key={p.platform} className="health-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{p.platform}</span>
                  <span className={`status-badge ${p.success_rate >= 80 ? 'idle' : p.success_rate >= 50 ? 'paused' : 'error'}`}>
                    {p.success_rate}% success
                  </span>
                </div>
                <div className="health-bar">
                  <div
                    className={`health-bar-fill ${p.success_rate >= 80 ? 'good' : p.success_rate >= 50 ? 'warning' : 'bad'}`}
                    style={{ width: `${p.success_rate}%` }}
                  ></div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  <span>{p.total_runs} runs</span>
                  <span>{p.total_new_jobs} jobs found</span>
                  <span>{p.avg_duration_seconds}s avg</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            No scrape runs yet. Create an engine and run it to see health data.
          </p>
        )}
      </div>

      {/* Recent Scrape Runs */}
      {health?.recent_runs?.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">📜 Recent Scrape Runs</h3>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Platform</th>
                <th>Status</th>
                <th>Jobs Found</th>
                <th>New</th>
                <th>Duration</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {health.recent_runs.slice(0, 10).map((run) => (
                <tr key={run.id}>
                  <td style={{ textTransform: 'capitalize', fontWeight: 500 }}>{run.platform_name}</td>
                  <td>
                    <span className={`status-badge ${run.status}`}>{run.status}</span>
                  </td>
                  <td>{run.jobs_found}</td>
                  <td style={{ color: 'var(--success)' }}>{run.jobs_new}</td>
                  <td>{run.duration_seconds ? `${run.duration_seconds.toFixed(1)}s` : '-'}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
