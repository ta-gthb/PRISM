// ─── Legal Metrology Authentication & Identity Module ──────────────────
// Manages departmental credentials, citizen/manufacturer OTP verification, and resilient session persistence

let _sbClient = null;

function initSupabase() {
  if (_sbClient) return _sbClient;
  if (!CONFIG.SUPABASE_URL || !CONFIG.SUPABASE_ANON_KEY) {
    return null;
  }
  try {
    if (window.supabase && typeof window.supabase.createClient === 'function') {
      _sbClient = window.supabase.createClient(
        CONFIG.SUPABASE_URL,
        CONFIG.SUPABASE_ANON_KEY
      );
      return _sbClient;
    }
  } catch (e) {
    console.warn('Supabase initialization warning:', e);
  }
  return null;
}

// ─── Session Store & Retrieval (Dual Storage for iFrame Reliability) ──
function persistSession(session) {
  try {
    sessionStorage.setItem('lm_session', JSON.stringify(session));
  } catch (_) {}
  try {
    localStorage.setItem('lm_session', JSON.stringify(session));
    localStorage.setItem('prism_auth', JSON.stringify(session));
  } catch (_) {}
}

function clearSession() {
  try {
    sessionStorage.removeItem('lm_session');
    sessionStorage.removeItem('lm_otp_mobile');
    sessionStorage.removeItem('lm_otp_state');
  } catch (_) {}
  try {
    localStorage.removeItem('lm_session');
    localStorage.removeItem('prism_auth');
  } catch (_) {}
}

// ─── Password-based Login (Admin / Inspector / Supervisor) ──────────
async function loginWithPassword(role, rawUserId, rawPassword) {
  const userId = (rawUserId || '').trim();
  const password = (rawPassword || '').trim();
  const cleanRole = (role || 'inspector').toLowerCase();

  if (!userId || !password) {
    return { success: false, error: 'Please provide both User ID and password.' };
  }

  // 1. Authenticate via Server API
  try {
    const data = await API.loginStaff(userId, password, cleanRole);
    if (data && (data.token || data.access_token)) {
      const session = {
        access_token: data.token || data.access_token,
        refresh_token: data.refresh_token || ('prism_refresh_' + Date.now()),
        role: data.role || cleanRole,
        userId: data.user_id || userId,
        user_id: data.user_id || userId,
        name: data.name || (userId.charAt(0).toUpperCase() + userId.slice(1)),
        email: data.email || `${userId}@doca.gov.in`,
        state: data.state || 'Delhi',
        organization: data.organization || 'Department of Consumer Affairs',
        designation: data.designation || (cleanRole === 'admin' ? 'System Administrator' : cleanRole === 'supervisor' ? 'Nodal Officer' : 'Field Inspector'),
        is_active: true
      };
      persistSession(session);
      return { success: true, role: session.role };
    }
  } catch (e) {
    console.warn('Server authentication response:', e);
    if (e.message && e.message.toLowerCase().includes('invalid')) {
      return { success: false, error: e.message };
    }
  }

  // 2. Try Supabase direct authentication if configured
  const sb = initSupabase();
  if (sb) {
    try {
      const email = userId.includes('@') ? userId : `${userId}@doca.gov.in`;
      const { data, error } = await sb.auth.signInWithPassword({ email, password });
      if (!error && data && data.session) {
        const session = {
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          role: cleanRole,
          userId: userId,
          user_id: userId,
          name: data.user.user_metadata?.full_name || userId,
          email: data.user.email,
          state: data.user.user_metadata?.state || 'Delhi',
          organization: 'Department of Consumer Affairs',
          is_active: true
        };
        persistSession(session);
        return { success: true, role: cleanRole };
      }
    } catch (err) {
      console.warn('Supabase password auth error:', err);
    }
  }

  return { 
    success: false, 
    error: 'Invalid User ID or password. Please verify your credentials and try again.' 
  };
}

// ─── OTP-based Login (Manufacturer / Consumer) ──────────────────────
async function requestOTP(mobile, state) {
  const cleanMobile = (mobile || '').replace(/\D/g, '');
  sessionStorage.setItem('lm_otp_mobile', cleanMobile);
  sessionStorage.setItem('lm_otp_state', state || 'Delhi');

  try {
    await API.requestOTP(cleanMobile);
  } catch (e) {
    console.warn('OTP request API response:', e);
  }

  const sb = initSupabase();
  if (sb) {
    try {
      const phone = `+91${cleanMobile}`;
      await sb.auth.signInWithOtp({ phone, options: { data: { state } } });
    } catch (err) {
      console.warn('Supabase OTP request error:', err);
    }
  }

  return { success: true };
}

async function verifyOTP(role, rawMobile, rawOtp) {
  const mobile = (rawMobile || '').replace(/\D/g, '');
  const otp = (rawOtp || '').trim();
  const state = sessionStorage.getItem('lm_otp_state') || 'Delhi';
  const cleanRole = role || 'consumer';

  if (!otp || otp.length < 4) {
    return { success: false, error: 'Please enter the complete verification code.' };
  }

  // 1. Verify through Server API
  try {
    const res = await API.verifyOTP(mobile, otp, cleanRole);
    if (res && (res.token || res.access_token || res.user_id)) {
      const publicId = res.user_id || (cleanRole === 'manufacturer'
        ? `MFR91_${new Date().getFullYear()}_${String(mobile).slice(-4)}`
        : `CTZN91_${new Date().getFullYear()}_${String(mobile).slice(-4)}`);

      const session = {
        access_token: res.token || res.access_token || ('prism_otp_' + Date.now()),
        refresh_token: res.refresh_token || ('prism_otp_ref_' + Date.now()),
        role: cleanRole,
        mobile: mobile,
        userId: publicId,
        user_id: publicId,
        name: cleanRole === 'manufacturer' ? 'Packaged Commodities Registered Manufacturer' : 'Citizen Consumer',
        email: `${cleanRole}_${mobile}@doca.gov.in`,
        state: state,
        organization: cleanRole === 'manufacturer' ? 'Legal Metrology Registered Packager' : 'Consumer Protection Portal',
        needsOnboarding: false,
        is_active: true
      };
      persistSession(session);
      return { success: true, isNew: false, role: cleanRole };
    }
  } catch (e) {
    console.warn('API OTP verify error:', e);
    if (e.message && (e.message.toLowerCase().includes('invalid') || e.message.toLowerCase().includes('expired'))) {
      return { success: false, error: e.message };
    }
  }

  // 2. Verify through Supabase Auth if configured
  const sb = initSupabase();
  if (sb) {
    try {
      const phone = `+91${mobile}`;
      const { data, error } = await sb.auth.verifyOtp({ phone, token: otp, type: 'sms' });
      if (!error && data && data.session) {
        const publicId = cleanRole === 'manufacturer'
          ? `MFR91_${new Date().getFullYear()}_${String(mobile).slice(-4)}`
          : `CTZN91_${new Date().getFullYear()}_${String(mobile).slice(-4)}`;

        const session = {
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          role: cleanRole,
          mobile,
          userId: publicId,
          user_id: publicId,
          name: cleanRole === 'manufacturer' ? 'Registered Manufacturer' : 'Citizen Consumer',
          email: `${cleanRole}_${mobile}@doca.gov.in`,
          state,
          needsOnboarding: false,
          is_active: true
        };
        persistSession(session);
        return { success: true, isNew: false, role: cleanRole };
      }
    } catch (err) {
      console.warn('Supabase verify error:', err);
    }
  }

  return { success: false, error: 'Invalid or expired verification code. Please check the code and try again.' };
}

// ─── Session Helpers ────────────────────────────────────────────────
function getSession() {
  try {
    const raw = sessionStorage.getItem('lm_session') || localStorage.getItem('lm_session') || localStorage.getItem('prism_auth');
    if (!raw) return null;
    const s = JSON.parse(raw);
    return s && (s.userId || s.user_id || s.role) ? s : null;
  } catch { return null; }
}

function requireAuth(expectedRole) {
  const session = getSession();
  if (!session) {
    window.location.href = '/';
    return null;
  }
  if (expectedRole && session.role !== expectedRole) {
    window.location.href = '/';
    return null;
  }
  return session;
}

async function logout() {
  clearSession();
  if (_sbClient) {
    await _sbClient.auth.signOut().catch(() => {});
  }
  window.location.href = '/';
}

// ─── JWT Header for API calls ───────────────────────────────────────
function getAuthHeader() {
  const session = getSession();
  if (!session) return {};
  const token = session.access_token || session.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

