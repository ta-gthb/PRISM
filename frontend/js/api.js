// ─── FastAPI Client ─────────────────────────────────────────────────

async function apiRequest(method, path, body = null, isFormData = false) {
  const url = `${CONFIG.API_BASE_URL}${path}`;
  const headers = { ...getAuthHeader() };
  if (!isFormData) headers['Content-Type'] = 'application/json';

  const opts = { method, headers };
  if (body) opts.body = isFormData ? body : JSON.stringify(body);

  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const API = {
  // Auth
  verifyToken: (token, requestedRole) => apiRequest('POST', '/api/auth/verify', { token, requested_role: requestedRole }),
  requestOTP:  (mobile) => apiRequest('POST', '/api/auth/otp/request', { mobile }),
  verifyOTP:   (mobile, otp, role) => apiRequest('POST', '/api/auth/otp/verify', { mobile, otp, role }),

  // Dashboard
  getStats:      () => apiRequest('GET', '/api/dashboard/stats'),
  getViolations: (params = '') => apiRequest('GET', `/api/dashboard/violations?${params}`),

  // Scan
  scanImage:      (formData) => apiRequest('POST', '/api/scan/image', formData, true),
  getScan:        (id) => apiRequest('GET', `/api/scan/${id}`),
  getScanHistory: (params = '') => apiRequest('GET', `/api/scan/history?${params}`),

  // Repository / Products
  getProducts: (params = '') => apiRequest('GET', `/api/products?${params}`),
  getProduct:  (id) => apiRequest('GET', `/api/products/${id}`),

  // Reports
  getReports:     (params = '') => apiRequest('GET', `/api/reports?${params}`),
  generateReport: (body) => apiRequest('POST', '/api/reports/generate', {
    title:       body.title || 'Compliance Report',
    report_type: body.report_type || (body.type === 'product_scan' ? 'product' : body.type) || 'summary',
    format:      body.format || 'pdf',
    filters:     body.filters || (body.period ? { period: body.period } : {}),
  }),
  downloadReport: (id, fmt) => `${CONFIG.API_BASE_URL}/api/reports/${id}/download?format=${fmt}`,

  // Users (admin only)
  getUsers:   () => apiRequest('GET', '/api/users'),
  createUser: (body) => apiRequest('POST', '/api/users', body),
  updateUser: (id, body) => apiRequest('PUT', `/api/users/${id}`, body),
  deleteUser: (id) => apiRequest('DELETE', `/api/users/${id}`),

  // Consumer violation escalation
  consumerReport: (scanId) => apiRequest('POST', `/api/scan/${scanId}/consumer-report`),
};
