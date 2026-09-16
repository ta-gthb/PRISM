// ─── Supabase Auth Integration ──────────────────────────────────────
// Uses @supabase/supabase-js loaded via CDN

let _sbClient = null;

function initSupabase() {
  if (_sbClient) return _sbClient;
  _sbClient = window.supabase.createClient(
    CONFIG.SUPABASE_URL,
    CONFIG.SUPABASE_ANON_KEY
  );
  return _sbClient;
}

// ─── Role → Supabase email mapping ──────────────────────────────────
function roleToEmail(userId) {
  return `${userId}@legalmetro.gov.in`;
}

// ─── Password-based login (Admin / Inspector / Supervisor) ──────────
async function loginWithPassword(role, userId, password) {
  const sb = initSupabase();
  const email = roleToEmail(userId);

  const { data, error } = await sb.auth.signInWithPassword({ email, password });
  if (error) {
    return { success: false, error: error.message };
  }

  try {
    await API.verifyToken(data.session.access_token, role);
  } catch (e) {
    console.warn('Token verification failed, continuing with Supabase session:', e.message);
  }

  const session = { ...data.session, role, userId };
  sessionStorage.setItem('lm_session', JSON.stringify(session));
  return { success: true, role };
}

// ─── OTP-based login (Manufacturer / Consumer) ──────────────────────
async function requestOTP(mobile) {
  const sb = initSupabase();
  const phone = `+91${mobile}`;
  const { error } = await sb.auth.signInWithOtp({ phone });
  if (error) throw error;
  return { success: true };
}

async function verifyOTP(role, mobile, otp) {
  const sb = initSupabase();
  const phone = `+91${mobile}`;
  const { data, error } = await sb.auth.verifyOtp({ phone, token: otp, type: 'sms' });
  if (error) return { success: false, error: error.message };

  let provisionedUser = null;
  try {
    provisionedUser = await API.verifyToken(data.session.access_token, role);
  } catch (e) {
    console.warn('Provisioning call failed:', e.message);
  }

  const isNew = provisionedUser?.is_new ?? false;
  const session = {
    ...data.session,
    role,
    mobile,
    userId: provisionedUser?.user_id || data.user?.id,
    needsOnboarding: isNew && role === 'manufacturer',
  };
  sessionStorage.setItem('lm_session', JSON.stringify(session));
  return { success: true, isNew, role };
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
