"""Repository, live dashboard metrics, and enforcement case queue."""

import json
import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from db.connection import get_db_connection
from models.schemas import (
    ConsumerCaseUpdate, ProductListResponse, ProductResponse,
    RuleThresholdsResponse, RuleThresholdsUpdate,
)
from routers.auth_router import get_current_user

router = APIRouter(tags=["Products & Dashboard"])


def _scope(role: str, user: dict, alias: str = "s") -> tuple[str, list]:
    if role == "admin":
        return "", []
    if role == "supervisor":
        return f"JOIN users scoped_user ON scoped_user.id = {alias}.user_id WHERE scoped_user.state = %s", [user.get("state")]
    return f"WHERE {alias}.user_id = %s", [str(user["id"])]


@router.get("/api/products", response_model=ProductListResponse)
def list_products(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), compliance_status: Optional[str] = None, search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    conditions, params = [], []
    role = current_user["role"]
    if role == "manufacturer":
        conditions.append("manufacturer_id = %s")
        params.append(str(current_user["id"]))
    elif role in ("inspector", "consumer"):
        conditions.append("EXISTS (SELECT 1 FROM scans owned WHERE owned.product_name = products.name AND owned.user_id = %s)")
        params.append(str(current_user["id"]))
    elif role == "supervisor":
        conditions.append("EXISTS (SELECT 1 FROM scans state_scan JOIN users state_user ON state_user.id=state_scan.user_id WHERE state_scan.product_name=products.name AND state_user.state=%s)")
        params.append(current_user.get("state"))
    if compliance_status in ("compliant", "partial", "violation", "unknown"):
        conditions.append("compliance_status = %s")
        params.append(compliance_status)
    if search:
        conditions.append("(name ILIKE %s OR brand ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) AS total FROM products {where}", params)
        total = cur.fetchone()["total"]
        cur.execute(f"SELECT * FROM products {where} ORDER BY last_scanned_at DESC NULLS LAST LIMIT %s OFFSET %s", [*params, page_size, (page - 1) * page_size])
        return ProductListResponse(items=[dict(row) for row in cur.fetchall()], total=total, page=page, page_size=page_size, total_pages=math.ceil(total / page_size) if total else 0)
    finally:
        conn.close()


@router.get("/api/products/{product_id}")
def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        cur.execute("SELECT id, product_name, brand, compliance_result, compliance_score, created_at FROM scans WHERE product_name=%s ORDER BY created_at DESC LIMIT 10", (product["name"],))
        scans = [dict(row) for row in cur.fetchall()]
        return {**dict(product), "recent_scans": scans}
    finally:
        conn.close()


@router.get("/api/dashboard/stats")
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    scope, params = _scope(current_user["role"], current_user)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Kolkata') AT TIME ZONE 'Asia/Kolkata') AS today, COUNT(*) FILTER (WHERE compliance_result='compliant') AS compliant, COUNT(*) FILTER (WHERE compliance_result='partial') AS partial, COUNT(*) FILTER (WHERE compliance_result='violation') AS violation, COALESCE(ROUND(AVG(compliance_score), 1), 0) AS average_score FROM scans s {scope}", params)
        row = dict(cur.fetchone())
        cur.execute(f"SELECT COUNT(*) AS count FROM violations v JOIN scans s ON s.id=v.scan_id {scope.replace('WHERE', 'WHERE', 1)}" if scope else "SELECT COUNT(*) AS count FROM violations", params)
        violations = cur.fetchone()["count"]
        cur.execute(f"SELECT COUNT(*) AS count FROM violations v JOIN scans s ON s.id=v.scan_id {scope + (' AND' if scope else ' WHERE') } v.severity='critical'", params)
        critical = cur.fetchone()["count"]

        admin_state = current_user.get("state")
        user_where = ""
        user_params = []
        if admin_state and admin_state.lower() not in ("all", "national", ""):
            user_where = "WHERE state = %s"
            user_params = [admin_state]

        cur.execute(f"SELECT COUNT(*) AS total FROM users {user_where}", user_params)
        total_users = cur.fetchone()["total"]

        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE role = 'inspector') AS total_inspectors,
                COUNT(*) FILTER (WHERE role = 'inspector' AND is_active = TRUE) AS active_inspectors,
                COUNT(*) FILTER (WHERE role = 'supervisor') AS total_supervisors,
                COUNT(*) FILTER (WHERE role = 'supervisor' AND is_active = TRUE) AS active_supervisors,
                COUNT(*) FILTER (WHERE role = 'admin') AS total_admins
            FROM users {user_where}
        """, user_params)
        user_counts = dict(cur.fetchone() or {})

        total = row["total"] or 0
        return {
            "total_scans": total,
            "scans_today": row["today"],
            "today_scans": row["today"],
            "compliance_rate": round((row["compliant"] or 0) / total * 100, 1) if total else 0,
            "compliance_breakdown": {
                "compliant": row["compliant"],
                "partial": row["partial"],
                "violation": row["violation"]
            },
            "compliant": row["compliant"],
            "violations": violations,
            "total_violations": violations,
            "critical_violations": critical,
            "average_score": float(row["average_score"]),
            "active_inspectors": user_counts.get("active_inspectors", 0),
            "total_users": total_users,
            "total_inspectors": user_counts.get("total_inspectors", 0),
            "total_supervisors": user_counts.get("total_supervisors", 0),
            "active_supervisors": user_counts.get("active_supervisors", 0),
            "total_admins": user_counts.get("total_admins", 0),
            "jurisdiction_state": admin_state or "All"
        }
    finally:
        conn.close()


@router.get("/api/rules/thresholds", response_model=RuleThresholdsResponse)
def get_rule_thresholds(current_user: dict = Depends(get_current_user)):
    state = current_user.get("state") or "Delhi"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM state_rule_thresholds WHERE state = %s", (state,))
        row = cur.fetchone()
        if row:
            return RuleThresholdsResponse(
                state=row["state"],
                critical_threshold=row["critical_threshold"],
                major_threshold=row["major_threshold"],
                auto_flag_below=row["auto_flag_below"],
                updated_at=row.get("updated_at")
            )
        return RuleThresholdsResponse(
            state=state,
            critical_threshold=40,
            major_threshold=65,
            auto_flag_below=50,
            updated_at=None
        )
    finally:
        conn.close()


@router.put("/api/rules/thresholds", response_model=RuleThresholdsResponse)
def update_rule_thresholds(body: RuleThresholdsUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only System Administrators can configure rule engine thresholds.")
    state = current_user.get("state") or "Delhi"
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO state_rule_thresholds (state, critical_threshold, major_threshold, auto_flag_below, updated_by, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (state) DO UPDATE SET
                critical_threshold = EXCLUDED.critical_threshold,
                major_threshold = EXCLUDED.major_threshold,
                auto_flag_below = EXCLUDED.auto_flag_below,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            RETURNING *
        """, (state, body.critical_threshold, body.major_threshold, body.auto_flag_below, current_user.get("id")))
        row = cur.fetchone()

        try:
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, resource, details)
                VALUES (%s, %s, %s, %s)
            """, (current_user["id"], "rule_thresholds_updated", "rules", json.dumps({"state": state, "critical_threshold": body.critical_threshold, "major_threshold": body.major_threshold, "auto_flag_below": body.auto_flag_below})))
        except Exception:
            pass

        conn.commit()
        return RuleThresholdsResponse(
            state=row["state"],
            critical_threshold=row["critical_threshold"],
            major_threshold=row["major_threshold"],
            auto_flag_below=row["auto_flag_below"],
            updated_at=row.get("updated_at")
        )
    finally:
        conn.close()


@router.get("/api/dashboard/violations")
def get_recent_violations(limit: int = Query(20, ge=1, le=100), severity: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    scope, params = _scope(current_user["role"], current_user)
    conditions = [scope] if scope else []
    if severity in ("critical", "major", "minor"):
        conditions.append("v.severity=%s")
        params.append(severity)
    where = " ".join(conditions)
    if where and not where.lstrip().startswith("JOIN"):
        where = " " + where
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT v.*, s.product_name, u.name AS inspector_name FROM violations v JOIN scans s ON s.id=v.scan_id JOIN users u ON u.id=s.user_id {where} ORDER BY v.created_at DESC LIMIT %s", [*params, limit])
        items = [dict(row) for row in cur.fetchall()]
        return {"items": items, "total": len(items)}
    finally:
        conn.close()


@router.get("/api/cases")
def list_consumer_cases(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "supervisor", "inspector"):
        raise HTTPException(status_code=403, detail="Enforcement access required")
    conditions, params = [], []
    if current_user["role"] != "admin":
        conditions.append("c.state=%s")
        params.append(current_user.get("state"))
    if status:
        conditions.append("c.status=%s")
        params.append(status)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT c.*, s.product_name, s.image_url, u.name AS consumer_name FROM consumer_cases c JOIN scans s ON s.id=c.scan_id JOIN users u ON u.id=s.user_id {where} ORDER BY c.created_at DESC", params)
        return {"items": [dict(row) for row in cur.fetchall()]}
    finally:
        conn.close()
