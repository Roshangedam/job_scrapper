'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const [emailConfig, setEmailConfig] = useState({
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_email: '',
    smtp_password: '',
    use_tls: true,
  });
  const [emailSaving, setEmailSaving] = useState(false);
  const [emailTesting, setEmailTesting] = useState(false);
  const [platforms, setPlatforms] = useState([]);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    try {
      const [emailData, platformData] = await Promise.all([
        api.getEmailConfig(),
        api.getPlatforms(),
      ]);

      if (emailData.config) {
        setEmailConfig(prev => ({ ...prev, ...emailData.config }));
      }
      setPlatforms(platformData.platforms);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  async function handleEmailSave(e) {
    e.preventDefault();
    setEmailSaving(true);
    try {
      await api.updateEmailConfig(emailConfig);
      alert('Email configuration saved!');
    } catch (err) {
      alert('Failed to save: ' + err.message);
    } finally {
      setEmailSaving(false);
    }
  }

  async function handleEmailTest() {
    setEmailTesting(true);
    setTestResult(null);
    try {
      const result = await api.testEmailConnection(emailConfig);
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: err.message });
    } finally {
      setEmailTesting(false);
    }
  }

  function handleEmailChange(e) {
    const { name, value, type, checked } = e.target;
    setEmailConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }

  return (
    <div>
      <h1 className="page-title">Settings</h1>
      <p className="page-subtitle">Configure email alerts, platform credentials, and AI settings</p>

      {/* Email Configuration */}
      <div className="settings-section">
        <h3 className="settings-section-title">📧 Email Configuration</h3>
        <div className="card">
          <form onSubmit={handleEmailSave}>
            <div className="settings-grid">
              <div className="form-group">
                <label className="form-label">SMTP Host</label>
                <input
                  className="form-input"
                  name="smtp_host"
                  value={emailConfig.smtp_host}
                  onChange={handleEmailChange}
                  placeholder="smtp.gmail.com"
                />
              </div>
              <div className="form-group">
                <label className="form-label">SMTP Port</label>
                <input
                  className="form-input"
                  name="smtp_port"
                  type="number"
                  value={emailConfig.smtp_port}
                  onChange={handleEmailChange}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input
                  className="form-input"
                  name="smtp_email"
                  type="email"
                  value={emailConfig.smtp_email}
                  onChange={handleEmailChange}
                  placeholder="your@gmail.com"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password / App Password</label>
                <input
                  className="form-input"
                  name="smtp_password"
                  type="password"
                  value={emailConfig.smtp_password}
                  onChange={handleEmailChange}
                  placeholder="App password"
                />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  name="use_tls"
                  checked={emailConfig.use_tls}
                  onChange={handleEmailChange}
                />
                Use TLS
              </label>
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
              <button type="submit" className="btn btn-primary" disabled={emailSaving}>
                {emailSaving ? '⏳ Saving...' : '💾 Save Email Config'}
              </button>
              <button type="button" className="btn btn-secondary" onClick={handleEmailTest} disabled={emailTesting}>
                {emailTesting ? '⏳ Testing...' : '🧪 Test Connection'}
              </button>
            </div>

            {testResult && (
              <div style={{
                marginTop: '12px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '13px',
                background: testResult.success ? 'var(--success-bg)' : 'var(--danger-bg)',
                color: testResult.success ? 'var(--success)' : 'var(--danger)',
              }}>
                {testResult.success ? '✅' : '❌'} {testResult.message}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Platform Configuration */}
      <div className="settings-section">
        <h3 className="settings-section-title">🌐 Platform Configuration</h3>
        {platforms.length === 0 ? (
          <div className="card">
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
              No platforms discovered. Make sure the backend is running with adapters.
            </p>
          </div>
        ) : (
          <div className="settings-grid">
            {platforms.map(p => (
              <div key={p.id} className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '20px' }}>
                    {p.name === 'naukri' ? '🟦' : p.name === 'linkedin' ? '🔵' : '🌐'}
                  </span>
                  <div>
                    <h4 style={{ fontSize: '15px', fontWeight: 600 }}>{p.display_name}</h4>
                    <span className={`status-badge ${p.is_available ? 'idle' : 'error'}`}>
                      {p.is_available ? 'Available' : 'Unavailable'}
                    </span>
                  </div>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                  {p.description || 'Configure authentication and proxy settings for this platform.'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Configuration Info */}
      <div className="settings-section">
        <h3 className="settings-section-title">🤖 AI Configuration</h3>
        <div className="card">
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
            AI providers are configured via environment variables in the backend <code>.env</code> file.
          </p>
          <div className="settings-grid">
            <div style={{ padding: '12px', background: 'var(--surface-1)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Primary Provider</div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--accent-primary)' }}>Google Gemini (Free)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>GEMINI_API_KEY in .env</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--surface-1)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Fallback Provider</div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--accent-secondary)' }}>Groq / Llama 3.3 (Free)</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>GROQ_API_KEY in .env</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
