/**
 * API Client Utility — communicates with FastAPI backend.
 */

const API_BASE = '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
    ...options,
  };

  if (options.body && !(options.body instanceof FormData)) {
    config.body = JSON.stringify(options.body);
  }

  const res = await fetch(url, config);

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API Error: ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Dashboard
  getDashboardStats: () => request('/dashboard/stats'),
  getScrapeHealth: () => request('/dashboard/scrape-health'),

  // Engines
  getEngines: () => request('/engines'),
  getEngine: (id) => request(`/engines/${id}`),
  createEngine: (formData) => request('/engines', { method: 'POST', body: formData, headers: {} }),
  updateEngine: (id, data) => request(`/engines/${id}`, { method: 'PUT', body: data }),
  deleteEngine: (id) => request(`/engines/${id}`, { method: 'DELETE' }),
  runEngine: (id) => request(`/engines/${id}/run`, { method: 'POST' }),
  uploadResume: (id, formData) => request(`/engines/${id}/resume`, { method: 'POST', body: formData, headers: {} }),

  // Jobs
  getJobs: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '') query.append(k, v);
    });
    return request(`/jobs?${query.toString()}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  deleteJob: (id) => request(`/jobs/${id}`, { method: 'DELETE' }),

  // Platforms
  getPlatforms: () => request('/platforms'),
  getPlatformConfig: (id) => request(`/platforms/${id}/config`),
  updatePlatformConfig: (id, configs) => request(`/platforms/${id}/config`, { method: 'PUT', body: configs }),

  // Settings
  getEmailConfig: () => request('/settings/email'),
  updateEmailConfig: (data) => request('/settings/email', { method: 'PUT', body: data }),
  testEmailConnection: (data) => request('/settings/email/test', { method: 'POST', body: data }),
  getAppSettings: (category) => request(`/settings/app${category ? `?category=${category}` : ''}`),
  updateAppSetting: (data) => request('/settings/app', { method: 'PUT', body: data }),

  // Health
  healthCheck: () => request('/health'),
};
