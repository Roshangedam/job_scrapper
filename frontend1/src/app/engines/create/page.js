'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useRouter } from 'next/navigation';

export default function CreateEnginePage() {
  const router = useRouter();
  const [platforms, setPlatforms] = useState([]);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    name: '',
    email: '',
    refresh_interval_minutes: 60,
    selectedPlatforms: [],
    keywords: '',
    companies: '',
    locations: '',
    experience_min: '',
    experience_max: '',
    resume: null,
  });

  useEffect(() => {
    api.getPlatforms().then(data => setPlatforms(data.platforms)).catch(console.error);
  }, []);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  }

  function handlePlatformToggle(platformId) {
    setForm(prev => ({
      ...prev,
      selectedPlatforms: prev.selectedPlatforms.includes(platformId)
        ? prev.selectedPlatforms.filter(id => id !== platformId)
        : [...prev.selectedPlatforms, platformId]
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('name', form.name);
      formData.append('email', form.email);
      formData.append('refresh_interval_minutes', form.refresh_interval_minutes);
      formData.append('platform_ids', JSON.stringify(form.selectedPlatforms));

      const keywords = form.keywords.split(',').map(s => s.trim()).filter(Boolean);
      const companies = form.companies.split(',').map(s => s.trim()).filter(Boolean);
      const locations = form.locations.split(',').map(s => s.trim()).filter(Boolean);

      formData.append('keywords', JSON.stringify(keywords));
      formData.append('companies', JSON.stringify(companies));
      formData.append('locations', JSON.stringify(locations));

      if (form.experience_min) formData.append('experience_min', form.experience_min);
      if (form.experience_max) formData.append('experience_max', form.experience_max);
      if (form.resume) formData.append('resume', form.resume);

      await api.createEngine(formData);
      router.push('/engines');
    } catch (err) {
      alert('Failed to create engine: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="page-title">Create Scraping Engine</h1>
      <p className="page-subtitle">Configure a new engine to automatically find matching jobs</p>

      <form onSubmit={handleSubmit} style={{ maxWidth: '700px' }}>
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>📋 Basic Info</h3>

          <div className="form-group">
            <label className="form-label">Engine Name *</label>
            <input
              className="form-input"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="e.g., Backend Jobs - Pune"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Email (for job alerts) *</label>
            <input
              className="form-input"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              placeholder="your@email.com"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Refresh Interval (minutes)</label>
            <input
              className="form-input"
              name="refresh_interval_minutes"
              type="number"
              min="5"
              max="1440"
              value={form.refresh_interval_minutes}
              onChange={handleChange}
            />
          </div>
        </div>

        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>🌐 Platforms</h3>

          {platforms.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>No platforms available. Start the backend to discover adapters.</p>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {platforms.map(p => (
                <button
                  type="button"
                  key={p.id}
                  className={`btn ${form.selectedPlatforms.includes(p.id) ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => handlePlatformToggle(p.id)}
                  style={{ fontSize: '13px' }}
                >
                  {form.selectedPlatforms.includes(p.id) ? '✅' : '⬜'} {p.display_name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>🔍 Search Preferences</h3>

          <div className="form-group">
            <label className="form-label">Job Keywords (comma-separated)</label>
            <input
              className="form-input"
              name="keywords"
              value={form.keywords}
              onChange={handleChange}
              placeholder="e.g., Python Developer, Backend Engineer, Full Stack"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Companies (comma-separated)</label>
            <input
              className="form-input"
              name="companies"
              value={form.companies}
              onChange={handleChange}
              placeholder="e.g., Google, Microsoft, Amazon"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Locations (comma-separated)</label>
            <input
              className="form-input"
              name="locations"
              value={form.locations}
              onChange={handleChange}
              placeholder="e.g., Bangalore, Pune, Remote"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Min Experience (years)</label>
              <input
                className="form-input"
                name="experience_min"
                type="number"
                min="0"
                step="0.5"
                value={form.experience_min}
                onChange={handleChange}
                placeholder="0"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Max Experience (years)</label>
              <input
                className="form-input"
                name="experience_max"
                type="number"
                min="0"
                step="0.5"
                value={form.experience_max}
                onChange={handleChange}
                placeholder="10"
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>📄 Resume Upload</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginBottom: '12px' }}>
            Upload your resume (PDF, DOCX, or TXT). AI will parse it and use it for job matching.
          </p>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt"
            onChange={(e) => setForm(prev => ({ ...prev, resume: e.target.files[0] }))}
            style={{ color: 'var(--text-secondary)', fontSize: '14px' }}
          />
          {form.resume && (
            <p style={{ marginTop: '8px', color: 'var(--accent-primary)', fontSize: '13px' }}>
              📎 {form.resume.name}
            </p>
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? '⏳ Creating...' : '🚀 Create Engine'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => router.back()}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
