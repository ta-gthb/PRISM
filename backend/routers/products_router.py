"""
Products router — also hosts the dashboard endpoints.

Endpoints
---------
GET /api/products               — paginated product repository
GET /api/products/{id}          — product detail with recent scans
GET /api/dashboard/stats        — KPI statistics (role-scoped)
GET /api/dashboard/violations   — recent violation feed
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db.connection import get_db_connection
from models.schemas import DashboardStats, ProductListResponse, ProductResponse
from routers.auth_router import get_current_user

router = APIRouter(tags=["Products & Dashboard"])


# ===========================================================================
# Products
# ===========================================================================


@router.get("/api/products", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    compliance_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Filter by product name or brand"),
    current_user: dict = Depends(get_current_user),
):
    """Return a paginated list of products from the repository."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        conditions: list[str] = []
        params: list = []

        if compliance_status and compliance_status in (
            "compliant", "partial", "violation", "unknown"
        ):
            conditions.append("compliance_status = %s")
            params.append(compliance_status)

        if search:
            conditions.append("(name ILIKE %s OR brand ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        offset = (page - 1) * page_size

        cur.execute(f"SELECT COUNT(*) AS total FROM products {where}", params)
        total = (cur.fetchone() or {}).get("total", 0)

        cur.execute(
            f"""
            SELECT * FROM products
            {where}
            ORDER BY last_scanned_at DESC NULLS LAST, created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        items = [dict(r) for r in cur.fetchall()]

        return ProductListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
    finally:
        conn.close()


@router.get("/api/products/{product_id}", response_model=dict)
def get_product(
    product_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return a single product with its 10 most-recent scans."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        # Recent scans for this product (matched by name)
        cur.execute(
            """
            SELECT s.id, s.product_name, s.brand, s.compliance_result,
                   s.compliance_score, s.created_at,
                   u.name AS inspector_name
              FROM scans s
              LEFT JOIN users u ON u.id = s.user_id
             WHERE s.product_name = %s
             ORDER BY s.created_at DESC
             LIMIT 10
            """,
            (product["name"],),
        )
        recent_scans = [dict(r) for r in cur.fetchall()]

        return {**dict(product), "recent_scans": recent_scans}
    finally:
        conn.close()


# ===========================================================================
# Dashboard
# ===========================================================================


@router.get("/api/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """
    Return KPI statistics.

    - Admins: aggregate across all users
    - Inspectors / others: scoped to their own scan history
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        is_manager = current_user.get("role") in ("admin", "supervisor")
        user_filter = "" if is_manager else "WHERE user_id = %s"
        user_param = [] if is_manager else [str(current_user["id"])]

        # Total scans
        cur.execute(
            f"SELECT COUNT(*) AS c FROM scans {user_filter}",
            user_param,
        )
        total_scans = (cur.fetchone() or {}).get("c", 0)

        # Scans today
        today_filter = (
            "WHERE DATE(created_at) = CURRENT_DATE"
            if is_manager
            else "WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE"
        )
        cur.execute(f"SELECT COUNT(*) AS c FROM scans {today_filter}", user_param)
        scans_today = (cur.fetchone() or {}).get("c", 0)

        # Compliance breakdown
        cur.execute(
            f"""
            SELECT compliance_result, COUNT(*) AS c
              FROM scans
             {user_filter}
             GROUP BY compliance_result
            """,
            user_param,
        )
        breakdown = {"compliant": 0, "partial": 0, "violation": 0}
        for row in cur.fetchall():
            key = row["compliance_result"]
            if key in breakdown:
                breakdown[key] = row["c"]

        compliant_count = breakdown["compliant"]
        compliance_rate = (
            round(compliant_count / total_scans * 100, 1) if total_scans else 0.0
        )

        # Total violations
        violations_filter = (
            ""
            if is_manager
            else "JOIN scans s ON s.id = v.scan_id WHERE s.user_id = %s"
        )
        cur.execute(
            f"SELECT COUNT(*) AS c FROM violations v {violations_filter}",
            user_param,
        )
        total_violations = (cur.fetchone() or {}).get("c", 0)

        # Critical violations
        critical_filter = (
            "WHERE severity = 'critical'"
            if is_manager
            else "JOIN scans s ON s.id = v.scan_id WHERE s.user_id = %s AND v.severity = 'critical'"
        )
        cur.execute(
            f"SELECT COUNT(*) AS c FROM violations v {critical_filter}",
            user_param,
        )
        critical_violations = (cur.fetchone() or {}).get("c", 0)

        # Total distinct products
        cur.execute("SELECT COUNT(*) AS c FROM products")
        total_products = (cur.fetchone() or {}).get("c", 0)

        # Active inspectors (admin view only)
        active_inspectors = 0
        if is_manager:
            cur.execute(
                "SELECT COUNT(*) AS c FROM users WHERE role = 'inspector' AND is_active = TRUE"
            )
            active_inspectors = (cur.fetchone() or {}).get("c", 0)

        # Recent 5 scans
        recent_filter = (
            "" if is_manager else "WHERE user_id = %s"
        )
        cur.execute(
            f"""
            SELECT id, product_name, brand, image_url,
                   compliance_result, compliance_score, created_at
              FROM scans
             {recent_filter}
             ORDER BY created_at DESC
             LIMIT 5
            """,
            user_param,
        )
        recent_scans = [dict(r) for r in cur.fetchall()]

        from models.schemas import ComplianceBreakdown

        return DashboardStats(
            total_scans=total_scans,
            scans_today=scans_today,
            compliance_rate=compliance_rate,
            compliance_breakdown=ComplianceBreakdown(**breakdown),
            total_violations=total_violations,
            critical_violations=critical_violations,
            total_products=total_products,
            active_inspectors=active_inspectors,
            recent_scans=recent_scans,
        )
    finally:
        conn.close()


@router.get("/api/dashboard/violations", response_model=dict)
def get_recent_violations(
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Return recent violations with denormalised scan and inspector context.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        is_manager = current_user.get("role") in ("admin", "supervisor")

        conditions = []
        params: list = []

        if not is_manager:
            conditions.append("s.user_id = %s")
            params.append(str(current_user["id"]))

        if severity and severity in ("critical", "major", "minor"):
            conditions.append("v.severity = %s")
            params.append(severity)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cur.execute(
            f"""
            SELECT v.id, v.scan_id, v.rule_code, v.field_name,
                   v.issue_description, v.severity, v.created_at,
                   s.product_name, u.name AS inspector_name
              FROM violations v
              JOIN scans s ON s.id = v.scan_id
              LEFT JOIN users u ON u.id = s.user_id
             {where}
             ORDER BY v.created_at DESC
             LIMIT %s
            """,
            params + [limit],
        )
        violations = [dict(r) for r in cur.fetchall()]
        return {"items": violations, "total": len(violations)}
    finally:
        conn.close()
