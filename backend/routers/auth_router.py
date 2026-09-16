"""
Authentication router.

Endpoints
---------
POST /api/auth/verify       — verify a Supabase JWT, return user record
POST /api/auth/otp/request  — trigger Supabase Phone Auth OTP
POST /api/auth/otp/verify   — verify OTP, return session
GET  /api/auth/me           — return the current user's DB record
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError, jwt

from db.connection import get_db_connection
from models.schemas import (
    AuthSessionResponse,
    AuthVerifyRequest,
    OTPRequest,
    OTPVerifyRequest,
    UserResponse,
    UserRole,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def _decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase-issued JWT.
    Falls back to unverified decode when JWT_SECRET is not set (dev mode).
    """
    if SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return payload
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {exc}",
            )
    else:
        # Development: decode without verification
        try:
            return jwt.decode(
                token,
                "",
                algorithms=["HS256"],
                options={"verify_signature": False, "verify_aud": False},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not decode token",
            )


def _get_user_from_db(supabase_user_id: str) -> Optional[dict]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE supabase_user_id = %s AND is_active = TRUE",
            (supabase_user_id,),
        )
        return cur.fetchone()
    finally:
        conn.close()


def _provision_user(payload: dict, requested_role: Optional[UserRole]) -> dict:
    """Link a Supabase identity to an approved local role record.

    Staff accounts are pre-provisioned by an administrator. Self-service
    provisioning is limited to the two phone-OTP roles, preventing a caller
    from assigning themselves an enforcement or administrator role.
    """
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject missing")

    existing = _get_user_from_db(supabase_user_id)
    if existing:
        return existing

    email = payload.get("email")
    mobile = payload.get("phone")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if email:
            cur.execute("SELECT * FROM users WHERE email = %s AND is_active = TRUE", (email,))
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "UPDATE users SET supabase_user_id = %s, updated_at = NOW() WHERE id = %s RETURNING *",
                    (supabase_user_id, existing["id"]),
                )
                user = cur.fetchone()
                conn.commit()
                return dict(user)

        if requested_role not in (UserRole.manufacturer, UserRole.consumer):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff accounts must be provisioned by an administrator",
            )

        user_email = email or f"{supabase_user_id}@phone.legalmetro.local"
        name = payload.get("user_metadata", {}).get("full_name") or mobile or "LegalMetro user"
        cur.execute(
            """
            INSERT INTO users (user_id, supabase_user_id, email, name, mobile, role)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """,
            (f"{'MFR91' if requested_role == UserRole.manufacturer else 'CTZN91'}_{supabase_user_id[:8].upper()}", supabase_user_id, user_email, name, mobile, requested_role.value),
        )
        user = cur.fetchone()
        conn.commit()
        return dict(user)
    finally:
        conn.close()


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    FastAPI dependency: extract Bearer token from Authorization header,
    validate JWT and return the user row from the database.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or malformed",
        )
    token = authorization.split(" ", 1)[1]
    payload = _decode_jwt(token)
    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token does not contain a subject claim",
        )
    user = _get_user_from_db(supabase_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or account is inactive",
        )
    return dict(user)


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/verify", response_model=UserResponse)
def verify_token(body: AuthVerifyRequest):
    """
    Verify a Supabase JWT.  Returns the user record from the local DB.
    Creates a minimal record for new users not yet in the DB.
    """
    payload = _decode_jwt(body.token)
    return _provision_user(payload, body.requested_role)


@router.post("/otp/request", status_code=status.HTTP_200_OK)
async def request_otp(body: OTPRequest):
    """
    Trigger a Supabase Phone Auth OTP for the given mobile number.
    """
    import httpx

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on this server",
        )

    url = f"{SUPABASE_URL}/auth/v1/otp"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"phone": body.mobile},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    if resp.status_code not in (200, 204):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resp.json().get("error_description", "Failed to send OTP"),
        )

    return {"message": f"OTP sent to {body.mobile}"}


@router.post("/otp/verify", response_model=AuthSessionResponse)
async def verify_otp(body: OTPVerifyRequest):
    """
    Verify the OTP received on the mobile number and return a Supabase session.
    """
    import httpx

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase is not configured on this server",
        )

    url = f"{SUPABASE_URL}/auth/v1/verify"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"phone": body.mobile, "token": body.otp, "type": "sms"},
            headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        )

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=resp.json().get("error_description", "OTP verification failed"),
        )

    data = resp.json()
    session = data.get("session", data)
    access_token = session.get("access_token", "")

    # Sync user into local DB
    user_data = None
    if access_token:
        payload = _decode_jwt(access_token)
        supabase_uid = payload.get("sub")
        if supabase_uid:
            user_data = _provision_user(payload, body.requested_role)

    return AuthSessionResponse(
        access_token=access_token,
        refresh_token=session.get("refresh_token"),
        expires_in=session.get("expires_in"),
        user=UserResponse(**dict(user_data)) if user_data else None,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's full profile from the database."""
    return current_user
