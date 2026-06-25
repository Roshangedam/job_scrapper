'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import Link from 'next/link';

export default function EnginesPage() {
  const [engines, setEngines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadEngines(); }, []);

  async function loadEngines() {
    try {
      const data = await api.getEngines();
      setEngines(data.engines);
    } catch (err) {
      console.error('Failed to load engines:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRun(engineId) {
    try {
      await api.runEngine(engineId);
      loadEngines();
    } catch (err) {
      alert('Failed to run engine: ' + err.message);
    }
  }

  async function handleDelete(engineId) {
    if (!confirm('Delete this engine and all its data?')) return;
    try {
      await api.deleteEngine(engineId);
      loadEngines();
    } catch (err) {
      alert('Failed to delete: ' + err.message);
    }
  }

  if (loading) return <div className="loading-spinner"></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="page-title">Scraping Engines</h1>
          <p className="page-subtitle">{engines.length} engine{engines.length !== 1 ? 's' : ''} configured</p>
        </div>
        <Link href="/engines/create" className="btn btn-primary">
          ➕ Create Engine
        </Link>
      </div>

      {engines.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">⚙️</div>
          <h3 className="empty-state-title">No Engines Yet</h3>
          <p className="empty-state-desc">Create your first scraping engine to start finding jobs automatically.</p>
          <Link href="/engines/create" className="btn btn-primary">Create Engine</Link>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {engines.map((engine) => (
            <div key={engine.id} className="engine-card">
              <div className="engine-card-header">
                <div>
                  <h3 className="engine-card-name">{engine.name}</h3>
                  <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{engine.email}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`status-badge ${engine.status}`}>{engine.status}</span>
                  <span className={`status-badge ${engine.is_active ? 'idle' : 'paused'}`}>
                    {engine.is_active ? 'Active' : 'Paused'}
                  </span>
                </div>
              </div>

              <div className="engine-card-meta">
                <div className="engine-meta-item">
                  <div className="label">Platforms</div>
                  <div className="value">
                    {engine.platforms?.map(p => p.platform_display_name || p.platform_name).join(', ') || 'None'}
                  </div>
                </div>
                <div className="engine-meta-item">
                  <div className="label">Refresh Interval</div>
                  <div className="value">{engine.refresh_interval_minutes} min</div>
                </div>
                <div className="engine-meta-item">
                  <div className="label">Jobs Found</div>
                  <div className="value">{engine.total_jobs_found}</div>
                </div>
                <div className="engine-meta-item">
                  <div className="label">Resume</div>
                  <div className="value">{engine.has_resume ? '✅ Uploaded' : '❌ Not uploaded'}</div>
                </div>
                <div className="engine-meta-item">
                  <div className="label">AI Profile</div>
                  <div className="value">{engine.has_profile ? '✅ Parsed' : '❌ Not parsed'}</div>
                </div>
                <div className="engine-meta-item">
                  <div className="label">Last Run</div>
                  <div className="value">
                    {engine.last_run_at ? new Date(engine.last_run_at).toLocaleString() : 'Never'}
                  </div>
                </div>
              </div>

              {/* Search preferences */}
              {engine.search_preferences?.length > 0 && (
                <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {engine.search_preferences.map((sp) => (
                    <span key={sp.id} className={`tag tag-skill`}>
                      {sp.pref_type === 'keyword' ? '🔑' : sp.pref_type === 'company' ? '🏢' : '📍'}{' '}
                      {sp.pref_value}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', gap: '8px', marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-color)' }}>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => handleRun(engine.id)}
                  disabled={engine.status === 'running'}
                >
                  {engine.status === 'running' ? '⏳ Running...' : '▶️ Run Now'}
                </button>
                <Link href={`/engines/${engine.id}`} className="btn btn-secondary btn-sm">
                  ✏️ Edit
                </Link>
                <button className="btn btn-danger btn-sm" onClick={() => handleDelete(engine.id)}>
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
