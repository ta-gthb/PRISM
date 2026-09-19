"""
Scan router.

Endpoints
---------
POST /api/scan/image         — upload image, run OCR + rule engine + RAG, persist
GET  /api/scan/history       — paginated scan history for the current user
GET  /api/scan/{scan_id}     — retrieve a specific scan result
"""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from typing import List

from db.connection import get_db_connection
from models.schemas import ScanListResponse, ScanResponse
from routers.auth_router import get_current_user
from services.ocr_service import ocr_service
from services.rag_service import rag_service
from services.rule_engine import rule_engine
from services.storage_service import storage_service

router = APIRouter(prefix="/api/scan", tags=["Scans"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "image/bmp",
    "application/pdf",
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/image", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def scan_image(
    file: Optional[UploadFile] = File(None, description="Label image, PDF artwork proof, or listing screenshot"),
    input_type: str = Form("physical_package", description="Inspection mode: physical_package, artwork_design, or ecommerce_listing"),
    product_name: Optional[str] = Form(None),
    brand: Optional[str] = Form(None),
    product_url: Optional[str] = Form(None, description="E-commerce listing URL (Amazon, Flipkart, Blinkit, Zepto, etc.)"),
    listing_text: Optional[str] = Form(None, description="E-commerce listing title, seller, or specification text"),
    platform_name: Optional[str] = Form(None, description="Marketplace platform name"),
    artwork_type: Optional[str] = Form(None, description="Packaging format: pouch, carton, bottle, label"),
    evidence: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(get_current_user),
):
    """
    Inspection Pipeline supporting three input modes:
    1. Physical package images (on-pack camera / photos, OCR + LM(PC)R 2011 physical rules)
    2. Packaging artwork/design files (pre-press PDF / high-res artwork, PDP checks, metric symbol audit)
    3. E-commerce product listings (digital marketplace URL / screenshot / metadata, Rule 6(10) audit)
    """
    input_type = (input_type or "physical_package").lower()

    if current_user.get("role") == "manufacturer":
        if not current_user.get("name") or not current_user.get("organization") or not current_user.get("gstin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Manufacturer must enter Manufacturer Name, Company Name, and GSTIN to proceed further."
            )

    image_bytes: Optional[bytes] = None
    image_url: Optional[str] = None
    ocr_result: dict = {"fields": {}, "analysis": {}}

    if file:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type '{file.content_type}'. "
                       f"Accepted: {', '.join(ALLOWED_CONTENT_TYPES)}",
            )
        image_bytes = await file.read()
        if len(image_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file exceeds the 10 MB limit",
            )

        # Upload to storage
        ext = ".pdf" if file.content_type == "application/pdf" else ".jpg"
        safe_filename = f"{uuid.uuid4()}{ext}"
        image_url = storage_service.upload_label_image(
            image_bytes, safe_filename, file.content_type or "image/jpeg"
        )

        # Process image via OCR if raster image
        if file.content_type != "application/pdf":
            try:
                ocr_result = ocr_service.process_image(image_bytes)
            except Exception as exc:
                ocr_result = {"fields": {}, "analysis": {}}
        else:
            # Handle PDF artwork
            ocr_result = {
                "fields": {
                    "artwork_format": "PDF Vector / Pre-Press Proof",
                    "artwork_type": artwork_type or "Packaging Proof",
                },
                "analysis": {"readability_score": 95, "median_text_height_px": 14},
            }
    elif input_type != "ecommerce_listing":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A file upload is required for physical package and artwork inspections.",
        )

    extracted_fields: dict = ocr_result.get("fields", {})
    extracted_fields["input_type"] = input_type

    # E-commerce listing specific extraction & URL handling
    if input_type == "ecommerce_listing":
        if platform_name:
            extracted_fields["platform_name"] = platform_name
        if product_url:
            extracted_fields["product_url"] = product_url
            if not platform_name:
                url_lower = product_url.lower()
                if "amazon" in url_lower:
                    extracted_fields["platform_name"] = "Amazon India"
                elif "flipkart" in url_lower:
                    extracted_fields["platform_name"] = "Flipkart"
                elif "blinkit" in url_lower:
                    extracted_fields["platform_name"] = "Blinkit"
                elif "zepto" in url_lower:
                    extracted_fields["platform_name"] = "Zepto"
                elif "jiomart" in url_lower:
                    extracted_fields["platform_name"] = "JioMart"
                elif "bigbasket" in url_lower:
                    extracted_fields["platform_name"] = "BigBasket"
                else:
                    extracted_fields["platform_name"] = "E-Commerce Marketplace"
        if listing_text:
            extracted_fields["listing_text"] = listing_text

    if artwork_type:
        extracted_fields["artwork_type"] = artwork_type

    # Prefer form-supplied name/brand over OCR guess
    if product_name:
        extracted_fields["product_name"] = product_name
    if brand:
        extracted_fields["brand"] = brand

    # --- Rule engine tailored to input_type ---
    compliance = rule_engine.run(
        extracted_fields,
        ocr_result.get("analysis"),
        state=current_user.get("state"),
        input_type=input_type,
    )
    extracted_fields["_analysis"] = ocr_result.get("analysis", {})
    if compliance.get("artwork_clearance"):
        extracted_fields["artwork_clearance"] = compliance["artwork_clearance"]

    # --- RAG guidance ---
    rag_guidance = rag_service.get_compliance_guidance(compliance["violations"])

    # Attach per-violation RAG context
    for v in compliance["violations"]:
        v["rag_context"] = rag_service.explain_violation(
            v.get("rule_code", ""),
            v.get("field", ""),
            v.get("issue", ""),
        )

    # --- Persist to DB ---
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        scan_id = str(uuid.uuid4())

        # Insert scan row
        cur.execute(
            """
            INSERT INTO scans
                (id, user_id, product_name, brand, image_url, extracted_fields,
                 compliance_result, compliance_score, violations, rag_guidance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                scan_id,
                str(current_user["id"]),
                extracted_fields.get("product_name") or product_name,
                extracted_fields.get("brand") or brand,
                image_url,
                _jsonb(extracted_fields),
                compliance["compliance_result"],
                compliance["compliance_score"],
                _jsonb(compliance["violations"]),
                rag_guidance,
            ),
        )
        scan_row = cur.fetchone()

        # Attach supporting photographs to the scan record.
        for evidence_file in evidence:
            if evidence_file.content_type not in ALLOWED_CONTENT_TYPES:
                raise HTTPException(status_code=415, detail="Supporting evidence must be an image")
            evidence_bytes = await evidence_file.read()
            if not evidence_bytes or len(evidence_bytes) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(status_code=413, detail="Supporting evidence exceeds the 10 MB limit")
            evidence_url = storage_service.upload_evidence(evidence_bytes, evidence_file.filename or "evidence.jpg", evidence_file.content_type)
            cur.execute("INSERT INTO scan_evidence (scan_id, file_url, file_name, content_type) VALUES (%s,%s,%s,%s)", (scan_id, evidence_url, evidence_file.filename or "evidence.jpg", evidence_file.content_type))

        # Insert individual violation rows
        for v in compliance["violations"]:
            cur.execute(
                """
                INSERT INTO violations
                    (scan_id, rule_code, field_name, issue_description,
                     severity, legal_explanation, rag_context)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    scan_id,
                    v.get("rule_code", ""),
                    v.get("field", ""),
                    v.get("issue", ""),
                    v.get("severity", "minor"),
                    v.get("explanation", ""),
                    v.get("rag_context", ""),
                ),
            )

        # Upsert product by the stable name/brand pair. A nullable barcode
        # cannot be used as the conflict target because PostgreSQL permits
        # multiple NULL values in a UNIQUE column.
        _name = extracted_fields.get("product_name") or product_name
        _brand = extracted_fields.get("brand") or brand
        if _name:
            cur.execute(
                """
                UPDATE products
                   SET scan_count = scan_count + 1,
                       compliance_status = %s,
                       last_scanned_at = NOW()
                 WHERE name = %s AND (brand = %s OR brand IS NULL)
                RETURNING id
                """,
                (compliance["compliance_result"], _name, _brand),
            )
            if not cur.fetchone():
                cur.execute(
                    """INSERT INTO products (name, brand, compliance_status, scan_count, last_scanned_at)
                       VALUES (%s, %s, %s, 1, NOW())""",
                    (_name, _brand, compliance["compliance_result"]),
                )

        conn.commit()

        return dict(scan_row)
    except Exception as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while saving scan: {exc}",
        )
    finally:
        conn.close()


@router.get("/history", response_model=ScanListResponse)
def get_scan_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    compliance_result: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Paginated scan history.  Admins see all scans; other roles see only
    their own.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        role = current_user.get("role")
        offset = (page - 1) * page_size

        if role == "admin":
            base_conditions, base_params = [], []
        elif role == "supervisor":
            base_conditions, base_params = ["user_id IN (SELECT id FROM users WHERE state = %s)"], [current_user.get("state")]
        else:
            base_conditions, base_params = ["user_id = %s"], [str(current_user["id"])]

        if compliance_result and compliance_result in ("compliant", "partial", "violation"):
            base_conditions.append("compliance_result = %s")
            base_params.append(compliance_result)

        where_clause = ("WHERE " + " AND ".join(base_conditions)) if base_conditions else ""

        # Count
        cur.execute(
            f"SELECT COUNT(*) AS total FROM scans {where_clause}",
            base_params,
        )
        total = (cur.fetchone() or {}).get("total", 0)

        # Fetch
        cur.execute(
            f"""
            SELECT id, product_name, brand, image_url,
                   compliance_result, compliance_score, created_at
              FROM scans
             {where_clause}
             ORDER BY created_at DESC
             LIMIT %s OFFSET %s
            """,
            base_params + [page_size, offset],
        )
        items = [dict(r) for r in cur.fetchall()]

        return ScanListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )
    finally:
        conn.close()


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve a full scan record by its UUID."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM scans WHERE id = %s",
            (scan_id,),
        )
        scan = cur.fetchone()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )

        permitted = current_user.get("role") == "admin" or str(scan["user_id"]) == str(current_user["id"])
        if current_user.get("role") == "supervisor":
            cur.execute("SELECT state FROM users WHERE id=%s", (scan["user_id"],))
            permitted = (cur.fetchone() or {}).get("state") == current_user.get("state")
        if not permitted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this scan",
            )

        result = dict(scan)
        cur.execute("SELECT id, file_url, file_name, content_type, created_at FROM scan_evidence WHERE scan_id = %s ORDER BY created_at", (scan_id,))
        result["evidence"] = [dict(row) for row in cur.fetchall()]
        return result
    finally:
        conn.close()


@router.post("/{scan_id}/consumer-report", status_code=status.HTTP_200_OK)
def flag_consumer_report(
    scan_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Consumer flags a non-compliant scan for DoCA/inspector review."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if current_user.get("role") != "consumer":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only consumers can submit violation reports")
        cur.execute("SELECT id, user_id FROM scans WHERE id = %s", (scan_id,))
        scan = cur.fetchone()
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
        if str(scan["user_id"]) != str(current_user["id"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot report a scan that is not yours")
        cur.execute("UPDATE scans SET consumer_reported = TRUE WHERE id = %s", (scan_id,))
        cur.execute("""INSERT INTO consumer_cases (scan_id, state)
                       VALUES (%s, %s) ON CONFLICT (scan_id) DO NOTHING""", (scan_id, current_user.get("state")))
        cur.execute("INSERT INTO audit_logs (user_id, action, resource, details) VALUES (%s, 'consumer_reported', 'scan', %s)", (current_user["id"], _jsonb({"scan_id": scan_id})))
        conn.commit()
        return {"success": True, "message": "Violation reported to enforcement authorities."}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

import json as _json


def _jsonb(obj) -> str:
    """Serialise a Python object to a JSON string for psycopg2 JSONB binding."""
    return _json.dumps(obj, default=str)
