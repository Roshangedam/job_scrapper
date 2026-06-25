'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export default function EngineDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [engine, setEngine] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEngine();
  }, [params.id]);

  async function loadEngine() {
    try {
      const data = await api.getEngine(params.id);
      setEngine(data);
    } catch (err) {
      console.error('Failed to load engine:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRun() {
    try {
      const result = await api.runEngine(params.id);
      alert(`Engine run complete! New jobs: ${result.new_jobs}, Duplicates: ${result.duplicates}`);
      loadEngine();
    } catch (err) {
      alert('Failed: ' + err.message);
    }
  }

  async function handleToggleActive() {
    try {
      await api.updateEngine(params.id, { is_active: !engine.is_active });
      loadEngine();
    } catch (err) {
      alert('Failed: ' + err.message);
    }
  }

  async function handleResumeUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('resume', file);

    try {
      const result = await api.uploadResume(params.id, formData);
      alert(result.message);
      loadEngine();
    } catch (err) {
      alert('Upload failed: ' + err.message);
    }
  }

  if (loading) return <div className="loading-spinner"></div>;
  if (!engine) return <div className="empty-state"><h3>Engine not found</h3></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h1 className="page-title">{engine.name}</h1>
          <p className="page-subtitle">{engine.email}</p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <span className={`status-badge ${engine.status}`}>{engine.status}</span>
          <span className={`status-badge ${engine.is_active ? 'idle' : 'paused'}`}>
            {engine.is_active ? 'Active' : 'Paused'}
          </span>
        </div>
      </div>

      {/* Engine Info */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3 className="card-title" style={{ marginBottom: '16px' }}>⚙️ Engine Details</h3>
        <div className="engine-card-meta">
          <div className="engine-meta-item">
            <div className="label">Platforms</div>
            <div className="value">
              {engine.platforms?.map(p => p.platform_display_name || p.platform_name).join(', ') || 'None'}
            </div>
          </div>
          <div className="engine-meta-item">
            <div className="label">Refresh Interval</div>
            <div className="value">{engine.refresh_interval_minutes} minutes</div>
          </div>
          <div className="engine-meta-item">
            <div className="label">Total Jobs Found</div>
            <div className="value">{engine.total_jobs_found}</div>
          </div>
          <div className="engine-meta-item">
            <div className="label">Last Run</div>
            <div className="value">{engine.last_run_at ? new Date(engine.last_run_at).toLocaleString() : 'Never'}</div>
          </div>
          <div className="engine-meta-item">
            <div className="label">Created</div>
            <div className="value">{new Date(engine.created_at).toLocaleDateString()}</div>
          </div>
        </div>
      </div>

      {/* Search Preferences */}
      {engine.search_preferences?.length > 0 && (
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>🔍 Search Preferences</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {engine.search_preferences.map(sp => (
              <span key={sp.id} className="tag tag-skill">
                {sp.pref_type === 'keyword' ? '🔑' : sp.pref_type === 'company' ? '🏢' : sp.pref_type === 'location' ? '📍' : '💼'}{' '}
                {sp.pref_value}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Resume / Profile */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <h3 className="card-title" style={{ marginBottom: '16px' }}>📄 Resume & AI Profile</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '12px' }}>
          <span className={`status-badge ${engine.has_resume ? 'idle' : 'error'}`}>
            {engine.has_resume ? '✅ Resume Uploaded' : '❌ No Resume'}
          </span>
          <span className={`status-badge ${engine.has_profile ? 'idle' : 'error'}`}>
            {engine.has_profile ? '✅ AI Profile Parsed' : '❌ Not Parsed'}
          </span>
        </div>
        <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
          📤 Upload / Replace Resume
          <input type="file" accept=".pdf,.docx,.doc,.txt" onChange={handleResumeUpload} style={{ display: 'none' }} />
        </label>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <button className="btn btn-primary" onClick={handleRun} disabled={engine.status === 'running'}>
          {engine.status === 'running' ? '⏳ Running...' : '▶️ Run Now'}
        </button>
        <button className="btn btn-secondary" onClick={handleToggleActive}>
          {engine.is_active ? '⏸️ Pause Engine' : '▶️ Activate Engine'}
        </button>
        <button className="btn btn-secondary" onClick={() => router.push('/engines')}>
          ← Back to Engines
        </button>
      </div>
    </div>
  );
}
