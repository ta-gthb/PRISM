"""Administrator-only management of local role records and Supabase users."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client

from db.connection import get_db_connection
from models.schemas import UserCreate, UserResponse, UserRole, UserUpdate
from routers.auth_router import require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


def _user_payload(row: dict) -> dict:
    return dict(row)


@router.get("", response_model=dict)
def list_users(
    role: Optional[UserRole] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    conditions, params = [], []
    if role:
        conditions.append("role = %s")
        params.append(role.value)
    if state:
        conditions.append("state = %s")
        params.append(state)
    if search:
        conditions.append("(name ILIKE %s OR email ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) AS total FROM users {where}", params)
        total = (cur.fetchone() or {}).get("total", 0)
        cur.execute(
            f"SELECT * FROM users {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [page_size, offset],
        )
        return {"items": [_user_payload(row) for row in cur.fetchall()], "total": total, "page": page, "page_size": page_size}
    finally:
        conn.close()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, current_user: dict = Depends(require_admin)):
    supabase_user_id = None
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    if body.password and (not url or not key):
        raise HTTPException(status_code=503, detail="Supabase service credentials are required to create password accounts")
    if body.password:
        try:
            auth_user = create_client(url, key).auth.admin.create_user({
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
                "user_metadata": {"full_name": body.name, "role": body.role.value},
            }).user
            supabase_user_id = str(auth_user.id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not create Supabase user: {exc}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        user_id = body.user_id or f"{body.role.value[:3].upper()}91_{uuid.uuid4().hex[:8].upper()}"
        # Auto-assign state from admin for field roles
        state_to_use = body.state
        if body.role.value in ('inspector', 'supervisor'):
            state_to_use = current_user.get('state') or body.state
        cur.execute(
            """INSERT INTO users (user_id, supabase_user_id, role, name, email, mobile, organization, state, designation, gstin)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (user_id, supabase_user_id, body.role.value, body.name, str(body.email), body.mobile, body.organization, state_to_use, body.designation, body.gstin),
        )
        user = cur.fetchone()
        conn.commit()
        return _user_payload(user)
    finally:
        conn.close()


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, body: UserUpdate, current_user: dict = Depends(require_admin)):
    updates = {key: value.value if isinstance(value, UserRole) else value for key, value in body.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    assignments = ", ".join(f"{key} = %s" for key in updates)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE users SET {assignments}, updated_at = NOW() WHERE id = %s RETURNING *", list(updates.values()) + [user_id])
        user = cur.fetchone()
        conn.commit()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_payload(user)
    finally:
        conn.close()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: str, current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s", (user_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
    finally:
        conn.close()
