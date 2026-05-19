// API client — connects to FastAPI backend at localhost:8000

const BASE = 'http://localhost:8000';

async function fetchJSON(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  health:       ()  => fetchJSON('/api/health'),
  dashboard:    ()  => fetchJSON('/api/dashboard'),
  contacts:     (status) => fetchJSON(`/api/contacts${status ? `?status=${status}` : ''}`),
  throttle:     ()  => fetchJSON('/api/throttle'),
  logs:         (n) => fetchJSON(`/api/logs?lines=${n || 50}`),
  deals:        ()  => fetchJSON('/api/deals'),
  runNow:       ()  => fetchJSON('/api/run-now',       { method: 'POST' }),
  checkReplies: ()  => fetchJSON('/api/check-replies', { method: 'POST' }),
  checkStalled: ()  => fetchJSON('/api/check-stalled', { method: 'POST' }),

  // Sequences
  sequences: () => fetchJSON('/api/sequences'),
  createSequence: (name, lead_type, followup_date, contact_ids, expo_source = '') =>
    fetchJSON('/api/sequences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, lead_type, followup_date, contact_ids, expo_source }),
    }),

  // Templates
  getTemplates: () => fetchJSON('/api/templates'),
  saveTemplate: (key, subject, body) =>
    fetchJSON(`/api/templates/${key}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject, body }),
    }),
  resetTemplate: (key) =>
    fetchJSON(`/api/templates/${key}/reset`, { method: 'POST' }),
  previewTemplate: (key, firstname = 'Alex', expo_name = 'the expo') =>
    fetchJSON(`/api/templates/${key}/preview?firstname=${encodeURIComponent(firstname)}&expo_name=${encodeURIComponent(expo_name)}`),
};
