'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

function MatchBadge({ pct }) {
  if (!pct && pct !== 0) return null;
  const level = pct >= 75 ? 'high' : pct >= 50 ? 'mid' : 'low';
  return <span className={`match-badge ${level}`}>{Math.round(pct)}%</span>;
}

function JobDetailDialog({ job, onClose }) {
  if (!job) return null;

  let skills = [];
  try { skills = JSON.parse(job.required_skills || '[]'); } catch {}

  let preferredSkills = [];
  try { preferredSkills = JSON.parse(job.preferred_skills || '[]'); } catch {}

  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={e => e.stopPropagation()}>
        <div className="dialog-header">
          <h2 className="dialog-title">{job.title}</h2>
          <button className="dialog-close" onClick={onClose}>✕</button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <span style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            {job.company_name}
          </span>
          {job.company_rating && (
            <span style={{ fontSize: '13px', color: 'var(--warning)' }}>⭐ {job.company_rating}</span>
          )}
          <span className={`status-badge idle`} style={{ fontSize: '11px' }}>
            {job.source_platform.toUpperCase()}
          </span>
        </div>

        {/* Match Section */}
        {job.match_pct !== null && job.match_pct !== undefined && (
          <div className="card" style={{ marginBottom: '16px', padding: '16px' }}>
            <h4 style={{ marginBottom: '12px', fontSize: '14px' }}>🎯 AI Match Analysis</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Overall</div>
                <MatchBadge pct={job.match_pct} />
              </div>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Skills</div>
                <MatchBadge pct={job.skill_match_pct} />
              </div>
              <div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Experience</div>
                <MatchBadge pct={job.experience_match_pct} />
              </div>
            </div>
            {job.recommendation && (
              <div style={{ marginTop: '12px' }}>
                <span className={`recommendation-badge ${job.recommendation}`}>{job.recommendation.replace('_', ' ')}</span>
              </div>
            )}
            {job.ai_summary && (
              <p style={{ marginTop: '10px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {job.ai_summary}
              </p>
            )}
          </div>
        )}

        {/* Job Details */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>📍 Location</span>
            <p style={{ fontSize: '14px' }}>{job.location_city || 'Not specified'} {job.remote_type ? `(${job.remote_type})` : ''}</p>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>💼 Experience</span>
            <p style={{ fontSize: '14px' }}>
              {job.experience_min_years || '?'} - {job.experience_max_years || '?'} years
            </p>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>💰 Salary</span>
            <p style={{ fontSize: '14px' }}>
              {job.salary_min && job.salary_max
                ? `${(job.salary_min / 100000).toFixed(1)}L - ${(job.salary_max / 100000).toFixed(1)}L ${job.salary_currency}`
                : 'Not disclosed'}
            </p>
          </div>
          <div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>📅 Posted</span>
            <p style={{ fontSize: '14px' }}>{job.posted_date || 'Unknown'}</p>
          </div>
          {job.applicants_count && (
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>👥 Applicants</span>
              <p style={{ fontSize: '14px' }}>{job.applicants_count}</p>
            </div>
          )}
          {job.employment_type && (
            <div>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>📝 Type</span>
              <p style={{ fontSize: '14px', textTransform: 'capitalize' }}>{job.employment_type}</p>
            </div>
          )}
        </div>

        {/* Skills */}
        {skills.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Required Skills</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {skills.map((s, i) => <span key={i} className="tag tag-skill">{s}</span>)}
            </div>
          </div>
        )}

        {preferredSkills.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Preferred Skills</h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {preferredSkills.map((s, i) => <span key={i} className="tag tag-skill" style={{ opacity: 0.7 }}>{s}</span>)}
            </div>
          </div>
        )}

        {/* Description */}
        {job.description_clean && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>Description</h4>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: '200px', overflow: 'auto' }}>
              {job.description_clean}
            </div>
          </div>
        )}

        {/* HR Contact */}
        {(job.hr_name || job.hr_email) && (
          <div style={{ marginBottom: '16px', padding: '12px', background: 'var(--surface-1)', borderRadius: 'var(--radius-md)' }}>
            <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>📧 Contact</h4>
            {job.hr_name && <p style={{ fontSize: '14px' }}>{job.hr_name}</p>}
            {job.hr_email && <a href={`mailto:${job.hr_email}`} style={{ fontSize: '13px' }}>{job.hr_email}</a>}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
          {job.source_url && (
            <a href={job.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-primary">
              🔗 Apply on {job.source_platform}
            </a>
          )}
          <button className="btn btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);

  const [filters, setFilters] = useState({
    search: '',
    platform: '',
    company: '',
    location: '',
    min_match_pct: '',
    employment_type: '',
    sort_by: 'scraped_at',
    sort_order: 'desc',
    page: 1,
    page_size: 20,
  });

  useEffect(() => { loadJobs(); }, [filters]);

  async function loadJobs() {
    setLoading(true);
    try {
      const data = await api.getJobs(filters);
      setJobs(data.jobs);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  }

  function handleFilterChange(key, value) {
    setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
  }

  let skills;

  return (
    <div>
      <h1 className="page-title">Scraped Jobs</h1>
      <p className="page-subtitle">{total} jobs found</p>

      {/* Filters */}
      <div className="filters-bar">
        <input
          className="form-input"
          placeholder="🔍 Search jobs..."
          value={filters.search}
          onChange={e => handleFilterChange('search', e.target.value)}
          style={{ minWidth: '220px' }}
        />
        <input
          className="form-input"
          placeholder="🏢 Company"
          value={filters.company}
          onChange={e => handleFilterChange('company', e.target.value)}
        />
        <input
          className="form-input"
          placeholder="📍 Location"
          value={filters.location}
          onChange={e => handleFilterChange('location', e.target.value)}
        />
        <select
          className="form-select"
          value={filters.sort_by}
          onChange={e => handleFilterChange('sort_by', e.target.value)}
        >
          <option value="scraped_at">Sort: Recent</option>
          <option value="title">Sort: Title</option>
          <option value="company_name">Sort: Company</option>
        </select>
        <select
          className="form-select"
          value={filters.sort_order}
          onChange={e => handleFilterChange('sort_order', e.target.value)}
          style={{ minWidth: '100px' }}
        >
          <option value="desc">↓ Desc</option>
          <option value="asc">↑ Asc</option>
        </select>
      </div>

      {loading ? (
        <div className="loading-spinner"></div>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">💼</div>
          <h3 className="empty-state-title">No Jobs Found</h3>
          <p className="empty-state-desc">Run a scraping engine to start discovering jobs, or adjust your filters.</p>
        </div>
      ) : (
        <>
          <div className="jobs-grid">
            {jobs.map(job => {
              try { skills = JSON.parse(job.required_skills || '[]'); } catch { skills = []; }

              return (
                <div key={job.id} className="job-card">
                  <div className="job-card-header">
                    <h3 className="job-card-title">{job.title}</h3>
                    <MatchBadge pct={job.match_pct} />
                  </div>

                  <div className="job-card-company">
                    <span className="job-card-company-name">{job.company_name || 'Unknown Company'}</span>
                    {job.company_rating && (
                      <span style={{ fontSize: '12px', color: 'var(--warning)' }}>⭐ {job.company_rating}</span>
                    )}
                  </div>

                  <div className="job-card-meta">
                    {job.location_city && <span className="job-card-meta-item">📍 {job.location_city}</span>}
                    {(job.experience_min_years || job.experience_max_years) && (
                      <span className="job-card-meta-item">💼 {job.experience_min_years || 0}-{job.experience_max_years || '?'} yrs</span>
                    )}
                    {(job.salary_min || job.salary_max) && (
                      <span className="job-card-meta-item">
                        💰 {job.salary_min ? `${(job.salary_min/100000).toFixed(0)}L` : '?'}-{job.salary_max ? `${(job.salary_max/100000).toFixed(0)}L` : '?'}
                      </span>
                    )}
                    {job.employment_type && <span className="job-card-meta-item">📝 {job.employment_type}</span>}
                    {job.applicants_count && <span className="job-card-meta-item">👥 {job.applicants_count}</span>}
                  </div>

                  {skills.length > 0 && (
                    <div className="job-card-skills">
                      {skills.slice(0, 5).map((s, i) => <span key={i} className="tag tag-skill">{s}</span>)}
                      {skills.length > 5 && <span className="tag tag-skill" style={{ opacity: 0.6 }}>+{skills.length - 5}</span>}
                    </div>
                  )}

                  {job.recommendation && (
                    <div style={{ marginBottom: '10px' }}>
                      <span className={`recommendation-badge ${job.recommendation}`}>
                        {job.recommendation.replace('_', ' ')}
                      </span>
                    </div>
                  )}

                  <div className="job-card-footer">
                    <div className="job-card-platform">
                      {job.source_platform.toUpperCase()}
                    </div>
                    <div className="job-card-actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => setSelectedJob(job)}>
                        ℹ️ Info
                      </button>
                      {job.source_url && (
                        <a href={job.source_url} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-sm">
                          Apply →
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          <div className="pagination">
            <button
              className="btn btn-secondary btn-sm"
              disabled={filters.page <= 1}
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page - 1 }))}
            >
              ← Prev
            </button>
            <span className="page-info">
              Page {filters.page} of {Math.ceil(total / filters.page_size) || 1}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              disabled={filters.page >= Math.ceil(total / filters.page_size)}
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
            >
              Next →
            </button>
          </div>
        </>
      )}

      <JobDetailDialog job={selectedJob} onClose={() => setSelectedJob(null)} />
    </div>
  );
}
