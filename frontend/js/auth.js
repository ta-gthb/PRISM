// ─── Supabase Auth Integration ──────────────────────────────────────
// Uses @supabase/supabase-js loaded via CDN

let _sbClient = null;

function initSupabase() {
  if (_sbClient) return _sbClient;
  if (!CONFIG.SUPABASE_URL || !CONFIG.SUPABASE_ANON_KEY) {
    throw new Error('Authentication is not configured. Contact the system administrator.');
  }
  _sbClient = window.supabase.createClient(
    CONFIG.SUPABASE_URL,
    CONFIG.SUPABASE_ANON_KEY
  );
  return _sbClient;
}

// ─── Password-based login (Admin / Inspector / Supervisor) ──────────
async function loginWithPassword(role, userId, password) {
  try {
    const data = await API.loginStaff(userId, password, role);
    if (!data.user || data.user.role !== role) throw new Error('Your account is not provisioned for this role.');
    const session = { access_token: data.access_token, refresh_token: data.refresh_token, role, userId: data.user.user_id, ...data.user };
    sessionStorage.setItem('lm_session', JSON.stringify(session));
    return { success: true, role };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// ─── OTP-based login (Manufacturer / Consumer) ──────────────────────
function generateNextUserId(role) {
  const prefix = role === 'manufacturer' ? 'MFR91' : 'CTZN91';
  const currentYear = new Date().getFullYear();
  let users = {};
  try {
    users = JSON.parse(localStorage.getItem('prism_registered_users') || '{}');
  } catch (e) {}

  let maxSerial = 0;
  Object.values(users).forEach(u => {
    if (u && u.user_id && typeof u.user_id === 'string') {
      const uid = u.user_id;
      if (uid.startsWith(prefix + currentYear) || uid.startsWith(prefix + '_' + currentYear)) {
        const tail = uid.replace(prefix + '_' + currentYear + '_', '')
                        .replace(prefix + '_' + currentYear, '')
                        .replace(prefix + currentYear, '')
                        .replace(/^_+/, '');
        if (/^\d+$/.test(tail)) {
          maxSerial = Math.max(maxSerial, parseInt(tail, 10));
        }
      }
    }
  });
  const serial = maxSerial + 1;
  return `${prefix}${currentYear}${String(serial).padStart(4, '0')}`;
}

async function requestOTP(mobile, state) {
  sessionStorage.setItem('pending_otp_mobile', mobile || '');
  sessionStorage.setItem('pending_otp_state', state || 'Delhi');

  if (CONFIG.SUPABASE_URL && CONFIG.SUPABASE_ANON_KEY) {
    try {
      const sb = initSupabase();
      const phone = `+91${mobile}`;
      const { error } = await sb.auth.signInWithOtp({ phone, options: { data: { state } } });
      if (error) throw error;
      return { success: true };
    } catch (err) {
      console.warn('Supabase requestOTP unavailable or failed, fallback to demo/direct verification:', err);
    }
  }
  return { success: true };
}

async function verifyOTP(role, mobile, otp) {
  const state = sessionStorage.getItem('pending_otp_state') || 'Delhi';
  let data = null;
  let isNew = false;
  let provisionedUser = null;

  if (CONFIG.SUPABASE_URL && CONFIG.SUPABASE_ANON_KEY) {
    try {
      const sb = initSupabase();
      const phone = `+91${mobile}`;
      const res = await sb.auth.verifyOtp({ phone, token: otp, type: 'sms' });
      if (!res.error && res.data && res.data.session) {
        data = res.data;
        try {
          provisionedUser = await API.verifyToken(data.session.access_token, role);
          isNew = provisionedUser?.is_new ?? false;
        } catch (e) {
          console.warn('API.verifyToken failed:', e);
        }
      }
    } catch (err) {
      console.warn('Supabase verifyOtp failed or unavailable:', err);
    }
  }

  // If running in demo / local mode or backend did not provision:
  if (!provisionedUser) {
    let users = {};
    try {
      users = JSON.parse(localStorage.getItem('prism_registered_users') || '{}');
    } catch (e) {}

    const userKey = `${role}_${mobile}`;
    let user = users[userKey];
    if (!user) {
      // First time login -> Auto register!
      isNew = true;
      const publicId = generateNextUserId(role);
      user = {
        id: 'usr_' + Date.now(),
        user_id: publicId,
        role: role,
        mobile: mobile,
        state: state,
        name: role === 'consumer' ? 'Citizen (' + mobile + ')' : '',
        organization: '',
        company_name: '',
        gstin: '',
        created_at: new Date().toISOString(),
        is_new: true,
      };
      users[userKey] = user;
      localStorage.setItem('prism_registered_users', JSON.stringify(users));
    } else {
      isNew = false;
    }
    provisionedUser = user;
  }

  const userId = provisionedUser.user_id;
  // Manufacturer must complete registration: Manufacturer Name, Company Name, and GSTIN
  const isMfrIncomplete = role === 'manufacturer' && (
    isNew ||
    !provisionedUser.name ||
    provisionedUser.name === mobile ||
    !provisionedUser.organization ||
    !provisionedUser.gstin
  );

  const session = {
    access_token: data?.session?.access_token || ('demo_token_' + Date.now()),
    refresh_token: data?.session?.refresh_token || '',
    role,
    mobile,
    userId: userId,
    ...provisionedUser,
    needsOnboarding: isMfrIncomplete,
  };
  sessionStorage.setItem('lm_session', JSON.stringify(session));
  return { success: true, isNew, role, userId, needsOnboarding: isMfrIncomplete };
}

// ─── Session helpers ────────────────────────────────────────────────
function getSession() {
  try {
    const raw = sessionStorage.getItem('lm_session');
    return raw ? JSON.parse(raw) : null;
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
  sessionStorage.removeItem('lm_session');
  if (_sbClient) {
    await _sbClient.auth.signOut().catch(() => {});
  }
  window.location.href = '/';
}

// ─── Supabase JWT for API calls ──────────────────────────────────────
function getAuthHeader() {
  const session = getSession();
  if (!session) return {};
  const token = session.access_token || session.token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
