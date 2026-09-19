"""Authentication and self-service profile endpoints."""

import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from db.connection import get_db_connection
from models.schemas import (
    AdminCredentialsUpdate, AuthSessionResponse, AuthVerifyRequest, OTPRequest, OTPVerifyRequest,
    ProfileUpdate, StaffLoginRequest, UserResponse, UserRole,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def _require_auth_configuration() -> None:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=503, detail="Authentication service is not configured")


def _decode_jwt(token: str) -> dict:
    _require_auth_configuration()
    # Fast path: decode locally if SUPABASE_JWT_SECRET (Legacy JWT Secret) is configured
    if SUPABASE_JWT_SECRET:
        try:
            return jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        except JWTError:
            pass  # Fall through to Supabase API verification (e.g. for asymmetric keys or rotation)

    # Fallback: verify via Supabase /auth/v1/user endpoint (supports both legacy HS256 and new asymmetric keys)
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": SUPABASE_ANON_KEY,
                },
            )
            if resp.status_code == 200:
                user_data = resp.json()
                return {
                    "sub": user_data.get("id"),
                    "email": user_data.get("email"),
                    "phone": user_data.get("phone"),
                    "user_metadata": user_data.get("user_metadata", {}),
                    "app_metadata": user_data.get("app_metadata", {}),
                }
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {exc}") from exc

    raise HTTPException(status_code=401, detail="Invalid or expired access token")


def _format_user_dict(row: Optional[dict]) -> Optional[dict]:
    if not row:
        return None
    d = dict(row)
    now = datetime.now(timezone.utc)
    for key in ("created_at", "updated_at"):
        val = d.get(key)
        if not val:
            d[key] = now
        elif isinstance(val, str):
            cleaned = re.sub(r'([+-]\d{2})$', r'\1:00', val.strip())
            try:
                d[key] = datetime.fromisoformat(cleaned)
            except Exception:
                try:
                    d[key] = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S.%f%z")
                except Exception:
                    d[key] = now
    return d


def _get_user(supabase_user_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE supabase_user_id = %s AND is_active = TRUE", (supabase_user_id,))
        row = cur.fetchone()
        return _format_user_dict(row)
    finally:
        conn.close()


def _next_public_id(cur, role: UserRole) -> str:
    prefix = "MFR91" if role == UserRole.manufacturer else "CTZN91"
    year = str(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).year)
    cur.execute("SELECT COUNT(*) AS count FROM users WHERE user_id LIKE %s", (f"{prefix}{year}%",))
    serial = int(cur.fetchone()["count"]) + 1
    return f"{prefix}{year}{serial:06d}"


def _provision_phone_user(payload: dict, requested_role: Optional[UserRole]) -> tuple[dict, bool]:
    if requested_role not in (UserRole.manufacturer, UserRole.consumer):
        raise HTTPException(status_code=403, detail="Only consumer and manufacturer phone accounts can self-register")
    subject = payload.get("sub")
    mobile = payload.get("phone")
    state = payload.get("user_metadata", {}).get("state")
    if not subject or not mobile or not state:
        raise HTTPException(status_code=401, detail="Phone identity is incomplete")
    existing = _get_user(subject)
    if existing:
        if existing["role"] != requested_role.value:
            raise HTTPException(status_code=403, detail="This phone number is already registered for another role")
        return existing, False
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE mobile = %s", (mobile,))
        existing = cur.fetchone()
        if existing:
            if existing["role"] != requested_role.value:
                raise HTTPException(status_code=403, detail="This phone number is already registered for another role")
            cur.execute("UPDATE users SET supabase_user_id=%s, updated_at=NOW() WHERE id=%s RETURNING *", (subject, existing["id"]))
            user = dict(cur.fetchone())
            conn.commit()
            return user, False
        public_id = _next_public_id(cur, requested_role)
        name = payload.get("user_metadata", {}).get("full_name") or mobile
        email = payload.get("email") or f"{subject}@phone.prism.invalid"
        cur.execute("""INSERT INTO users (user_id, supabase_user_id, role, name, email, mobile, state)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (public_id, subject, requested_role.value, name, email, mobile, state))
        user = dict(cur.fetchone())
        conn.commit()
        return user, True
    finally:
        conn.close()


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing or malformed")
    payload = _decode_jwt(authorization.split(" ", 1)[1])
    user = _get_user(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="User not found or account is inactive")
    return user


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


@router.post("/staff-login", response_model=AuthSessionResponse)
async def staff_login(body: StaffLoginRequest):
    _require_auth_configuration()
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=%s AND role=%s AND is_active=TRUE", (body.user_id, body.role.value))
        user = cur.fetchone()
    finally:
        conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user ID, role, or inactive account")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{SUPABASE_URL}/auth/v1/token?grant_type=password", json={"email": user["email"], "password": body.password}, headers={"apikey": SUPABASE_ANON_KEY})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session = response.json()
    payload = _decode_jwt(session["access_token"])
    if payload.get("sub") != user.get("supabase_user_id"):
        raise HTTPException(status_code=403, detail="Account identity is not linked to this user ID")
    formatted_user = _format_user_dict(user)
    return AuthSessionResponse(access_token=session["access_token"], refresh_token=session.get("refresh_token"), expires_in=session.get("expires_in"), user=UserResponse(**formatted_user))


@router.post("/verify", response_model=dict)
def verify_token(body: AuthVerifyRequest):
    payload = _decode_jwt(body.token)
    user, is_new = _provision_phone_user(payload, body.requested_role) if body.requested_role in (UserRole.manufacturer, UserRole.consumer) else (_get_user(payload.get("sub", "")), False)
    if not user:
        raise HTTPException(status_code=403, detail="Staff account is not provisioned")
    return {**user, "is_new": is_new}


@router.post("/otp/request")
async def request_otp(body: OTPRequest):
    _require_auth_configuration()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{SUPABASE_URL}/auth/v1/otp", json={"phone": body.mobile}, headers={"apikey": SUPABASE_ANON_KEY})
    if response.status_code not in (200, 204):
        raise HTTPException(status_code=400, detail="Could not send OTP")
    return {"message": "OTP sent"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(body: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    values = body.model_dump(exclude_none=True)
    if not values:
        raise HTTPException(status_code=400, detail="No profile changes supplied")
    if current_user["role"] == "manufacturer" and (not values.get("name") or not values.get("organization") or not values.get("gstin")):
        raise HTTPException(status_code=400, detail="Manufacturer name, company name, and GSTIN are required")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        assignments = ", ".join(f"{field}=%s" for field in values)
        cur.execute(f"UPDATE users SET {assignments}, updated_at=NOW() WHERE id=%s RETURNING *", [*values.values(), current_user["id"]])
        updated = dict(cur.fetchone())
        conn.commit()
        return updated
    finally:
        conn.close()


def _get_supabase_admin():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if url and key:
        try:
            from supabase import create_client
            return create_client(url, key).auth.admin
        except Exception:
            return None
    return None


@router.put("/credentials", response_model=UserResponse)
async def update_credentials(body: AdminCredentialsUpdate, current_user: dict = Depends(get_current_user)):
    """Allow updating login email and/or password for administrative accounts with mandatory current password verification."""
    supabase_user_id = current_user.get("supabase_user_id")
    if not supabase_user_id:
        raise HTTPException(status_code=400, detail="Account is not linked to authentication system")

    if not body.current_password or not body.current_password.strip():
        raise HTTPException(status_code=400, detail="Current password is mandatory to authorize credential updates")

    if SUPABASE_URL and SUPABASE_ANON_KEY:
        async with httpx.AsyncClient(timeout=20) as client:
            test_resp = await client.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": current_user["email"], "password": body.current_password},
                headers={"apikey": SUPABASE_ANON_KEY}
            )
            if test_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Current password verification failed. Please enter your valid current password.")

    auth_updates = {}
    if body.email and str(body.email).lower() != str(current_user["email"]).lower():
        auth_updates["email"] = str(body.email).lower()
        auth_updates["email_confirm"] = True
    if body.password:
        auth_updates["password"] = body.password

    if not auth_updates:
        raise HTTPException(status_code=400, detail="No new email or password provided")

    sb_admin = _get_supabase_admin()
    if sb_admin:
        try:
            sb_admin.update_user_by_id(supabase_user_id, auth_updates)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not update authentication credentials: {exc}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if "email" in auth_updates:
            cur.execute("UPDATE users SET email = %s, updated_at = NOW() WHERE id = %s RETURNING *", (auth_updates["email"], current_user["id"]))
            user = cur.fetchone()
        else:
            cur.execute("SELECT * FROM users WHERE id = %s", (current_user["id"],))
            user = cur.fetchone()

        try:
            cur.execute("INSERT INTO audit_logs (user_id, action, resource, details) VALUES (%s, %s, %s, %s)", (current_user["id"], "credentials_updated", "auth", json.dumps({"updated_fields": list(auth_updates.keys())})))
        except Exception:
            pass

        conn.commit()
        return _format_user_dict(dict(user))
    finally:
        conn.close()

