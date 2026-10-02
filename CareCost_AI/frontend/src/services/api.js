const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export async function estimateCost(payload) {
  return request('/v1/estimate', payload);
}

export async function calculateInsurance(payload) {
  return request('/v1/insurance/calculate', payload);
}

export async function login(payload) {
  return authRequest('/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) });
}

export async function getPatientOverview() { return getJson('/v1/patient/overview', 'Unable to load your patient overview.'); }
export async function getAgentOverview() { return getJson('/v1/agent/overview', 'Unable to load the agent overview.'); }
export async function searchPolicyholders(query = '') { return getJson(`/v1/agent/policyholders?search=${encodeURIComponent(query)}`, 'Unable to load policyholders.'); }
export async function getPolicyholder(signId) { return getJson(`/v1/agent/policyholders/${encodeURIComponent(signId)}`, 'Unable to load this policyholder.'); }
export async function reviewClaim(claimId, status) {
  const response = await fetch(`${API_BASE}/v1/agent/claims/${encodeURIComponent(claimId)}?status=${encodeURIComponent(status)}`, { method: 'PATCH', credentials: 'include' });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Unable to update claim status.');
  return body;
}

async function getJson(path, fallback) {
  let response;
  try { response = await fetch(`${API_BASE}${path}`, { credentials: 'include' }); }
  catch { throw new Error('Cannot reach CareCost AI. Check that the backend is running.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || fallback);
  return body;
}

export async function logout() {
  return authRequest('/v1/auth/logout', { method: 'POST' });
}

export async function getCurrentUser() {
  let response;
  try { response = await fetch(`${API_BASE}/v1/auth/me`, { credentials: 'include' }); }
  catch { throw new Error('Cannot reach CareCost AI. Check that the backend is running.'); }
  if (response.status === 401) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Unable to check the current session.');
  return body;
}

async function authRequest(path, { method, body } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body,
      credentials: 'include',
    });
  } catch {
    throw new Error('Cannot reach CareCost AI. Check that the backend is running.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to complete authentication.');
  return result;
}

async function request(path, payload) {
  let response;
  try { response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), credentials: 'include' }); }
  catch { throw new Error('Cannot reach CareCost AI. Check that the backend is running.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : 'Please check the form and try again.';
    throw new Error(detail);
  }
  return body;
}

export async function getDemoPolicy() {
  let response;
  try { response = await fetch(`${API_BASE}/v1/insurance/demo-policy`, { credentials: 'include' }); }
  catch { throw new Error('Cannot load the demo policy. Check that the backend is running.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Unable to load the demo policy.');
  return body;
}

export async function lookupCghs(code) {
  let response;
  try { response = await fetch(`${API_BASE}/v1/cghs/${encodeURIComponent(code)}`, { credentials: 'include' }); }
  catch { throw new Error('Cannot reach the CGHS reference service.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Unable to look up this CGHS code.');
  return body.results;
}

export async function uploadBill(file, onProgress = () => {}) {
  const form = new FormData();
  form.append('file', file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/v1/documents/upload`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onerror = () => reject(new Error('Cannot reach CareCost AI. Check that the backend is running.'));
    xhr.onload = () => {
      let body = {};
      try { body = JSON.parse(xhr.responseText); } catch { /* use the generic message */ }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(typeof body.detail === 'string' ? body.detail : 'The bill could not be uploaded.'));
        return;
      }
      resolve(body);
    };
    xhr.send(form);
  });
}

export async function getDocumentSummary(documentId) {
  let response;
  try { response = await fetch(`${API_BASE}/v1/documents/${encodeURIComponent(documentId)}`, { credentials: 'include' }); }
  catch { throw new Error('Cannot reach the document service.'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Unable to load the extracted bill details.');
  return body;
}
