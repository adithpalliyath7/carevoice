// API base URL. Empty by default = same origin: in local dev Vite proxies
// /api to http://localhost:8000 (see vite.config.js), and on Vercel the
// deployed frontend talks to the deployed backend on the same domain.
// Set VITE_API_URL only to point at a separately-hosted backend.
const BASE = import.meta.env.VITE_API_URL || ''

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, opts)
  const text = await res.text()
  let data = null
  try { data = JSON.parse(text) } catch { data = { raw: text } }
  if (!res.ok) {
    const err = new Error(data?.detail || data?.message || `HTTP ${res.status}`)
    err.status = res.status
    err.code = data?.error || data?.detail
    err.body = data
    throw err
  }
  return data
}

export const api = {
  health: () => req('/api/health'),
  languages: () => req('/api/voice/languages'),
  transcribe: async (blob, language) => {
    const fd = new FormData()
    fd.append('audio_file', blob, 'voice.webm')
    fd.append('language', language)
    return req('/api/voice/transcribe', { method: 'POST', body: fd })
  },
  speak: async ({ text, language, speed = 1, senior_mode = false }) => {
    const res = await fetch(BASE + '/api/voice/speak', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, language, speed, senior_mode }),
    })
    if (!res.ok) {
      const d = await res.json().catch(() => ({}))
      const e = new Error(d.message || `HTTP ${res.status}`); e.status = res.status; e.code = d.error
      throw e
    }
    return res.blob()
  },
  converse: (transcript, language, session, senior_mode) =>
    req('/api/voice/converse', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript, language, session, senior_mode }) }),
  doctors: (q = {}) => {
    const p = new URLSearchParams(q).toString()
    return req(`/api/doctors${p ? '?' + p : ''}`)
  },
  doctor: (id) => req(`/api/doctors/${id}`),
  slots: (id, date) => req(`/api/doctors/${id}/slots?date=${date}`),
  book: (payload) => req('/api/appointments', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  appointment: (token) => req(`/api/appointments/${token}`),
  queuePosition: (token) => req(`/api/appointments/${token}/queue-position`),
  checkIn: (token) => req(`/api/appointments/${token}/check-in`, { method: 'POST' }),
  reschedule: (token, date, time) => req(`/api/appointments/${token}/reschedule`,
    { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ date, time }) }),
  cancelAppointment: (token, reason) => req(`/api/appointments/${token}/cancel`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason, by: 'patient' }) }),
  emergency: (payload) => req('/api/support/emergency', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload || { language: 'en' }) }),
  emergencyDepartments: (lat, lng) =>
    req(`/api/support/emergency-departments${lat != null ? `?lat=${lat}&lng=${lng}` : ''}`),
  supportAsk: (question, language) => req('/api/support/ask', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, language }) }),
  glossary: (term, language) => req(`/api/support/glossary?term=${encodeURIComponent(term)}&language=${language}`),
  prepareVisit: (body) => req('/api/support/prepare-visit', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  postVisit: (token) => req(`/api/support/post-visit?appointment_token=${token}`),
  escalate: (body) => req('/api/support/escalate', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  // Records
  records: (q = {}) => { const p = new URLSearchParams(q).toString(); return req(`/api/records${p ? '?' + p : ''}`) },
  uploadRecord: (fd) => req('/api/records/upload', { method: 'POST', body: fd }),
  shareRecord: (id) => req(`/api/records/${id}/share`, { method: 'POST' }),
  recordVoiceSearch: (transcript) => req(`/api/records/search/voice?transcript=${encodeURIComponent(transcript)}`),
  createReminder: (body) => req('/api/records/reminders', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  reminders: () => req('/api/records/reminders'),
  // Waitlist
  joinWaitlist: (body) => req('/api/waitlist', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  waitlistEntry: (id) => req(`/api/waitlist/${id}`),
  waitlistAccept: (id, confirmed) => req(`/api/waitlist/${id}/accept`, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmed }) }),
  waitlistDecline: (id) => req(`/api/waitlist/${id}/decline`, { method: 'POST' }),
  // Ops (staff)
  opsLogin: (email, password) => req('/api/ops/login', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) }),
  opsAppointments: (role, params = {}) => {
    const p = new URLSearchParams(params).toString()
    return req(`/api/ops/appointments${p ? '?' + p : ''}`, { headers: { 'X-Demo-Role': role } })
  },
  opsQueue: (role, doctorId, date) => req(`/api/ops/queue?doctor_id=${doctorId}&date=${date}`, { headers: { 'X-Demo-Role': role } }),
  opsCallNext: (role, doctorId, date) => req(`/api/ops/queue/call-next?doctor_id=${doctorId}&date=${date}`, { method: 'POST', headers: { 'X-Demo-Role': role } }),
  opsQueueAction: (role, token, action) => req(`/api/ops/queue/${token}/${action}`, { method: 'POST', headers: { 'X-Demo-Role': role } }),
  opsCheckIn: (role, token) => req('/api/ops/check-in', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify({ token }) }),
  opsWalkIn: (role, body) => req('/api/ops/walk-in', { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify(body) }),
  opsAvailability: (role, doctorId) => req(`/api/ops/doctors/${doctorId}/availability`, { headers: { 'X-Demo-Role': role } }),
  opsSetAvailability: (role, doctorId, body) => req(`/api/ops/doctors/${doctorId}/availability`, { method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify(body) }),
  opsBlockSlot: (role, doctorId, body) => req(`/api/ops/doctors/${doctorId}/block-slot`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify(body) }),
  opsDelay: (role, doctorId, body) => req(`/api/ops/doctors/${doctorId}/delay`, { method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Demo-Role': role }, body: JSON.stringify(body) }),
  opsClearDelay: (role, doctorId) => req(`/api/ops/doctors/${doctorId}/delay/clear`, { method: 'POST', headers: { 'X-Demo-Role': role } }),
  opsCancellations: (role, date) => req(`/api/ops/cancellations${date ? '?date=' + date : ''}`, { headers: { 'X-Demo-Role': role } }),
  opsWaitlist: (role) => req('/api/ops/waitlist', { headers: { 'X-Demo-Role': role } }),
  opsAnalyticsDaily: (role, date) => req(`/api/ops/analytics/daily?date=${date}`, { headers: { 'X-Demo-Role': role } }),
  opsAnalyticsLanguage: (role) => req('/api/ops/analytics/language', { headers: { 'X-Demo-Role': role } }),
  opsAnalyticsOverview: (role) => req('/api/ops/analytics/overview', { headers: { 'X-Demo-Role': role } }),
  submitFeedback: (body) => req('/api/feedback', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
}
