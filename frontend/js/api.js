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

function normaliseScan(scan) {
  if (!scan) return scan;
  return {
    ...scan,
    status: scan.compliance_result || scan.status,
    score: scan.compliance_score ?? scan.score,
    scanned_at: scan.created_at || scan.scanned_at,
  };
}

async function getStats() {
  const stats = await apiRequest('GET', '/api/dashboard/stats');
  return {
    ...stats,
    today_violations: stats.total_violations || 0,
    avg_compliance_score: stats.average_score,
    compliant_products: stats.compliance_breakdown?.compliant || 0,
    products_with_violations: stats.compliance_breakdown?.violation || 0,
  };
}

const API = {
  health: () => apiRequest('GET', '/health'),
  // Auth
  loginStaff:  (userId, password, role) => apiRequest('POST', '/api/auth/staff-login', { user_id: userId, password, role }),
  verifyToken: (token, requestedRole) => apiRequest('POST', '/api/auth/verify', { token, requested_role: requestedRole }),
  getMe:       () => apiRequest('GET', '/api/auth/me'),
  updateMe:    async (body) => {
    try {
      return await apiRequest('PUT', '/api/auth/me', body);
    } catch (err) {
      // In preview or standalone frontend mode: update session & registered users storage
      let users = {};
      try { users = JSON.parse(localStorage.getItem('prism_registered_users') || '{}'); } catch (e) {}
      let session = {};
      try { session = JSON.parse(sessionStorage.getItem('lm_session') || '{}'); } catch (e) {}
      const updated = {
        ...session,
        name: body.name || session.name,
        organization: body.organization || session.organization,
        company_name: body.organization || session.company_name,
        gstin: body.gstin || session.gstin,
      };
      const userKey = `${session.role}_${session.mobile}`;
      if (users[userKey]) {
        users[userKey] = { ...users[userKey], ...updated };
        localStorage.setItem('prism_registered_users', JSON.stringify(users));
      }
      return updated;
    }
  },
  requestOTP:  (mobile) => apiRequest('POST', '/api/auth/otp/request', { mobile }),
  verifyOTP:   (mobile, otp, role) => apiRequest('POST', '/api/auth/otp/verify', { mobile, otp, role }),

  // Dashboard
  getStats,
  getViolations: async (params = '') => {
    const data = await apiRequest('GET', `/api/dashboard/violations?${params}`);
    return { ...data, items: (data.items || []).map(v => ({ ...v, product: v.product_name, field: v.field_name, date: v.created_at })) };
  },

  // Scan
  scanImage: async (formData) => normaliseScan(await apiRequest('POST', '/api/scan/image', formData, true)),
  getScan: async (id) => normaliseScan(await apiRequest('GET', `/api/scan/${id}`)),
  getScanHistory: async (params = '') => {
    const data = await apiRequest('GET', `/api/scan/history?${params}`);
    return { ...data, items: (data.items || []).map(normaliseScan) };
  },

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
  getUsers:   (params = '') => apiRequest('GET', `/api/users${params ? '?' + params : ''}`),
  createUser: (body) => apiRequest('POST', '/api/users', body),
  updateUser: (id, body) => apiRequest('PUT', `/api/users/${id}`, body),
  deleteUser: (id, permanent = true) => apiRequest('DELETE', `/api/users/${id}?permanent=${permanent}`),
  getAuditLogs: () => apiRequest('GET', '/api/users/audit-logs'),

  // Credentials & Rule Engine thresholds
  updateCredentials: (body) => apiRequest('PUT', '/api/auth/credentials', body),
  getRuleThresholds: () => apiRequest('GET', '/api/rules/thresholds'),
  updateRuleThresholds: (body) => apiRequest('PUT', '/api/rules/thresholds', body),

  // Consumer violation escalation
  consumerReport: (scanId) => apiRequest('POST', `/api/scan/${scanId}/consumer-report`),
  getCases: (params = '') => apiRequest('GET', `/api/cases?${params}`),
};
