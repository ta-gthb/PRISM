"""
Reports router.

Endpoints
---------
GET  /api/reports                — list reports for the current user
POST /api/reports/generate       — generate a PDF or Excel report
GET  /api/reports/{id}/download  — download a previously generated report
"""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
import httpx

from db.connection import get_db_connection
from models.schemas import ReportCreate, ReportResponse
from routers.auth_router import get_current_user
from services.report_service import report_service
from services.storage_service import storage_service

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# List reports
# ---------------------------------------------------------------------------


@router.get("", response_model=dict)
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """List all reports accessible to the current user."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        is_admin = current_user.get("role") == "admin"
        offset = (page - 1) * page_size

        if is_admin:
            cur.execute("SELECT COUNT(*) AS total FROM reports")
            total = (cur.fetchone() or {}).get("total", 0)
            cur.execute(
                "SELECT * FROM reports ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (page_size, offset),
            )
        else:
            user_id = str(current_user["id"])
            cur.execute(
                "SELECT COUNT(*) AS total FROM reports WHERE user_id = %s",
                (user_id,),
            )
            total = (cur.fetchone() or {}).get("total", 0)
            cur.execute(
                """
                SELECT * FROM reports
                 WHERE user_id = %s
                 ORDER BY created_at DESC
                 LIMIT %s OFFSET %s
                """,
                (user_id, page_size, offset),
            )

        items = [dict(r) for r in cur.fetchall()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total else 0,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Generate report
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    body: ReportCreate,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a PDF or Excel compliance report.

    Applies optional filters (date_from, date_to, compliance_result, state)
    to the scan data, renders the file, uploads to Supabase Storage, and
    stores the report metadata in the DB.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build dynamic WHERE clause from filters
        conditions = []
        params: list = []

        # Non-admins always scoped to their own scans
        if current_user.get("role") != "admin":
            conditions.append("s.user_id = %s")
            params.append(str(current_user["id"]))
        elif body.filters.get("user_id"):
            conditions.append("s.user_id = %s")
            params.append(str(body.filters["user_id"]))

        if body.filters.get("date_from"):
            conditions.append("s.created_at >= %s")
            params.append(body.filters["date_from"])

        if body.filters.get("date_to"):
            conditions.append("s.created_at <= %s")
            params.append(body.filters["date_to"])

        if body.filters.get("compliance_result"):
            conditions.append("s.compliance_result = %s")
            params.append(body.filters["compliance_result"])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cur.execute(
            f"""
            SELECT s.id, s.product_name, s.brand, s.compliance_result,
                   s.compliance_score, s.violations, s.created_at,
                   u.name AS inspector_name, u.state
              FROM scans s
              LEFT JOIN users u ON u.id = s.user_id
             {where_clause}
             ORDER BY s.created_at DESC
             LIMIT 5000
            """,
            params,
        )
        scans = [dict(r) for r in cur.fetchall()]

        # Generate file bytes
        report_format = body.format.value
        if report_format == "pdf":
            file_bytes = report_service.generate_pdf(
                title=body.title,
                scans=scans,
                filters=body.filters,
                generated_by=current_user.get("name", ""),
            )
            content_type = "application/pdf"
            ext = "pdf"
        elif report_format == "excel":
            file_bytes = report_service.generate_excel(
                title=body.title,
                scans=scans,
                filters=body.filters,
            )
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            ext = "xlsx"
        elif report_format == "csv":
            file_bytes = report_service.generate_csv(
                title=body.title,
                scans=scans,
                filters=body.filters,
            )
            content_type = "text/csv; charset=utf-8"
            ext = "csv"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported format '{report_format}'",
            )

        # Upload
        filename = f"report_{uuid.uuid4()}.{ext}"
        file_url = storage_service.upload_report(file_bytes, filename, content_type)

        # Persist metadata
        import json as _json

        report_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO reports (id, user_id, title, report_type, format, file_url, filters)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                report_id,
                str(current_user["id"]),
                body.title,
                body.report_type.value,
                report_format,
                file_url,
                _json.dumps(body.filters),
            ),
        )
        report_row = cur.fetchone()
        conn.commit()
        return dict(report_row)
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {exc}",
        )
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Stream the report file back to the client.  If the file is stored on
    Supabase Storage, proxy it through; otherwise return a 404.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
        report = cur.fetchone()
    finally:
        conn.close()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )

    # Access control
    if (
        current_user.get("role") != "admin"
        and str(report["user_id"]) != str(current_user["id"])
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    file_url = report.get("file_url", "")
    report_format = report.get("format", "pdf")

    content_type_map = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
    }
    content_type = content_type_map.get(report_format, "application/octet-stream")
    ext_map = {"pdf": "pdf", "excel": "xlsx", "csv": "csv"}
    ext = ext_map.get(report_format, "bin")
    safe_title = report.get("title", "report").replace(" ", "_")[:50]
    disposition = f'attachment; filename="{safe_title}.{ext}"'

    if file_url.startswith("http"):
        # Proxy the file from Supabase Storage
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            upstream = await client.get(file_url)
        if upstream.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Could not retrieve file from storage",
            )
        return Response(
            content=upstream.content,
            media_type=content_type,
            headers={"Content-Disposition": disposition},
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Report file URL is not available",
    )
