"""Administrator-only management of local role records and Supabase users."""

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import create_client

from db.connection import get_db_connection
from models.schemas import UserCreate, UserResponse, UserRole, UserUpdate
from routers.auth_router import require_admin

router = APIRouter(prefix="/api/users", tags=["Users"])


def _user_payload(row: dict) -> dict:
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


def _audit(cur, actor_id, action, resource, details):
    import json
    try:
        cur.execute("SAVEPOINT audit_sp")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = 'audit_logs' AND column_name = 'action'
                ) THEN
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS user_id UUID;
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS action TEXT;
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS resource TEXT;
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}';
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS ip_address INET;
                    ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
                END IF;
            END $$;
        """)
        cur.execute("INSERT INTO audit_logs (user_id, action, resource, details) VALUES (%s,%s,%s,%s)", (actor_id, action, resource, json.dumps(details)))
        cur.execute("RELEASE SAVEPOINT audit_sp")
    except Exception as exc:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT audit_sp")
        except Exception:
            pass
        print(f"Warning: could not write audit log: {exc}")


@router.get("", response_model=dict)
def list_users(
    role: Optional[UserRole] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    exclude_self: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    conditions, params = [], []
    if exclude_self and current_user.get("id"):
        conditions.append("id != %s")
        params.append(current_user["id"])
    
    # State scoping: A system administrator can only view the list of user accounts under their assigned state
    admin_state = current_user.get("state")
    if admin_state and admin_state.lower() not in ("all", "national", ""):
        conditions.append("state = %s")
        params.append(admin_state)
    elif state:
        conditions.append("state = %s")
        params.append(state)

    if role:
        conditions.append("role = %s")
        params.append(role.value)
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
    # Restrict creation under System Admin portal to Field Inspector and Supervisor accounts only
    if body.role not in (UserRole.inspector, UserRole.supervisor):
        raise HTTPException(
            status_code=400,
            detail="Under the System Administrator portal, only Field Inspector / Enforcement Officer and Supervisor / Nodal Officer accounts can be created."
        )
    if not body.password:
        raise HTTPException(status_code=400, detail="A password is required when provisioning a staff account")

    # Name handling with First Name & Last Name
    if body.first_name and body.last_name:
        full_name = f"{body.first_name.strip()} {body.last_name.strip()}"
    elif body.first_name:
        full_name = body.first_name.strip()
    else:
        full_name = body.name or "Staff User"

    # State is automatically allotted based on System Administrator assigned State
    admin_state = current_user.get('state') or 'Delhi'
    state_to_use = admin_state

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
                "user_metadata": {"full_name": full_name, "role": body.role.value},
            }).user
            supabase_user_id = str(auth_user.id)
        except Exception as exc:
            err_msg = str(exc).lower()
            if any(k in err_msg for k in ("already", "registered", "exists")):
                # Account already exists in Supabase Auth (e.g. after DB reinit or re-registration)
                # Locate existing auth account and update credentials & metadata
                sb_admin = create_client(url, key).auth.admin
                existing_auth_id = None
                try:
                    conn_check = get_db_connection()
                    try:
                        with conn_check.cursor() as cur_check:
                            cur_check.execute("SELECT id FROM auth.users WHERE LOWER(email) = LOWER(%s)", (body.email,))
                            arow = cur_check.fetchone()
                            if arow:
                                existing_auth_id = str(arow["id"] if isinstance(arow, dict) else arow[0])
                    finally:
                        conn_check.close()
                except Exception:
                    pass

                if not existing_auth_id:
                    try:
                        users_list = sb_admin.list_users()
                        all_users = getattr(users_list, "users", users_list) if not isinstance(users_list, list) else users_list
                        for u in all_users:
                            if getattr(u, "email", "").lower() == body.email.lower():
                                existing_auth_id = str(u.id)
                                break
                    except Exception:
                        pass

                if existing_auth_id:
                    sb_admin.update_user_by_id(
                        existing_auth_id,
                        {
                            "password": body.password,
                            "email_confirm": True,
                            "user_metadata": {"full_name": full_name, "role": body.role.value},
                        }
                    )
                    supabase_user_id = existing_auth_id
                else:
                    raise HTTPException(status_code=400, detail=f"Email '{body.email}' already exists in auth system, but could not sync credentials: {exc}")
            else:
                raise HTTPException(status_code=400, detail=f"Could not create Supabase user: {exc}")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if not body.user_id:
            if body.role in (UserRole.manufacturer, UserRole.consumer):
                from routers.auth_router import _next_public_id
                user_id = _next_public_id(cur, body.role)
            else:
                user_id = f"{body.role.value[:3].upper()}-{uuid.uuid4().hex[:10].upper()}"
        else:
            user_id = body.user_id

        # Check if user with same user_id OR email already exists in users table
        cur.execute("SELECT id, user_id, email, is_active FROM users WHERE user_id = %s OR LOWER(email) = LOWER(%s)", (user_id, str(body.email).lower()))
        existing_u = cur.fetchone()

        if existing_u:
            if existing_u["user_id"] != user_id and existing_u.get("is_active"):
                raise HTTPException(
                    status_code=409,
                    detail=f"A user with email '{body.email}' already exists in PRISM under User ID '{existing_u['user_id']}'."
                )
            cur.execute(
                """UPDATE users SET
                       user_id = %s, supabase_user_id = %s, role = %s, name = %s, email = %s,
                       mobile = %s, organization = %s, state = %s, designation = %s, gstin = %s,
                       is_active = TRUE, updated_at = NOW()
                   WHERE id = %s RETURNING *""",
                (user_id, supabase_user_id, body.role.value, full_name, str(body.email), body.mobile, body.organization, state_to_use, body.designation, body.gstin, existing_u["id"])
            )
            user = cur.fetchone()
            _audit(cur, current_user["id"], "user_updated", "user", {"user_id": user_id, "role": body.role.value})
        else:
            cur.execute(
                """INSERT INTO users (user_id, supabase_user_id, role, name, email, mobile, organization, state, designation, gstin, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING *""",
                (user_id, supabase_user_id, body.role.value, full_name, str(body.email), body.mobile, body.organization, state_to_use, body.designation, body.gstin),
            )
            user = cur.fetchone()
            _audit(cur, current_user["id"], "user_created", "user", {"user_id": user_id, "role": body.role.value})

        conn.commit()
        return _user_payload(user)
    finally:
        conn.close()


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, body: UserUpdate, current_user: dict = Depends(require_admin)):
    current_id = str(current_user.get("id", ""))
    current_uid = str(current_user.get("user_id", "")).lower()
    if body.is_active is False and (str(user_id) == current_id or str(user_id).lower() == current_uid):
        raise HTTPException(status_code=400, detail="System Administrators cannot deactivate their own account.")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s OR user_id = %s", (user_id, user_id))
        target = cur.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        # Jurisdiction check: Admin can only manage users within their assigned state
        admin_state = current_user.get("state")
        if admin_state and admin_state.lower() not in ("all", "national", ""):
            if target.get("state") and target["state"] != admin_state and target["role"] != "admin":
                raise HTTPException(status_code=403, detail=f"You can only manage users within your jurisdiction ({admin_state}).")

        # System administrator can edit the passwords of registered users
        if body.password:
            url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            if url and key and target.get("supabase_user_id"):
                try:
                    sb_admin = create_client(url, key).auth.admin
                    sb_admin.update_user_by_id(target["supabase_user_id"], {"password": body.password})
                except Exception as exc:
                    raise HTTPException(status_code=400, detail=f"Could not update password in auth service: {exc}")

        updates = {key: value.value if isinstance(value, UserRole) else value for key, value in body.model_dump(exclude_none=True).items()}
        updates.pop("password", None)

        first_name = updates.pop("first_name", None)
        last_name = updates.pop("last_name", None)
        if first_name and last_name:
            updates["name"] = f"{first_name.strip()} {last_name.strip()}"
        elif first_name:
            updates["name"] = first_name.strip()

        if target["role"] in ("inspector", "supervisor") and admin_state:
            updates["state"] = admin_state

        if not updates and not body.password:
            raise HTTPException(status_code=400, detail="No fields to update")

        if updates:
            assignments = ", ".join(f"{key} = %s" for key in updates)
            cur.execute(f"UPDATE users SET {assignments}, updated_at = NOW() WHERE id = %s RETURNING *", list(updates.values()) + [target["id"]])
            user = cur.fetchone()
        else:
            user = target

        _audit(cur, current_user["id"], "user_updated", "user", {"id": str(target["id"]), "fields": list(updates.keys()) + (["password"] if body.password else [])})
        conn.commit()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_payload(user)
    finally:
        conn.close()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, permanent: bool = Query(True), current_user: dict = Depends(require_admin)):
    current_id = str(current_user.get("id", ""))
    current_uid = str(current_user.get("user_id", "")).lower()
    if str(user_id) == current_id or str(user_id).lower() == current_uid:
        raise HTTPException(status_code=400, detail="System Administrators cannot delete or deactivate their own account.")

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s OR user_id = %s", (user_id, user_id))
        target = cur.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if str(target["id"]) == current_id or str(target.get("user_id", "")).lower() == current_uid:
            raise HTTPException(status_code=400, detail="System Administrators cannot delete or deactivate their own account.")

        admin_state = current_user.get("state")
        if admin_state and admin_state.lower() not in ("all", "national", ""):
            if target.get("state") and target["state"] != admin_state and target["role"] != "admin":
                raise HTTPException(status_code=403, detail=f"You can only manage users within your jurisdiction ({admin_state}).")

        if permanent:
            url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            if url and key and target.get("supabase_user_id"):
                try:
                    sb_admin = create_client(url, key).auth.admin
                    sb_admin.delete_user(target["supabase_user_id"])
                except Exception as exc:
                    print(f"Warning: could not delete Supabase auth user: {exc}")
            cur.execute("DELETE FROM users WHERE id = %s", (target["id"],))
            _audit(cur, current_user["id"], "user_deleted", "user", {"id": str(target["id"]), "user_id": target.get("user_id")})
        else:
            cur.execute("UPDATE users SET is_active = FALSE, updated_at = NOW() WHERE id = %s", (target["id"],))
            _audit(cur, current_user["id"], "user_deactivated", "user", {"id": str(target["id"]), "user_id": target.get("user_id")})

        conn.commit()
    finally:
        conn.close()


@router.get("/audit-logs", response_model=dict)
def audit_logs(limit: int = Query(100, ge=1, le=500), current_user: dict = Depends(require_admin)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""SELECT a.*, u.name AS actor_name FROM audit_logs a
                       LEFT JOIN users u ON u.id=a.user_id ORDER BY a.created_at DESC LIMIT %s""", (limit,))
        return {"items": [dict(row) for row in cur.fetchall()]}
    finally:
        conn.close()
