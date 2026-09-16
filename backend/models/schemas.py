"""
Pydantic v2 schemas for the Legal Metrology Compliance System.

All response models use model_config = ConfigDict(from_attributes=True) so
they can be constructed directly from psycopg2 RealDict rows.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ComplianceResult(str, Enum):
    compliant = "compliant"
    partial = "partial"
    violation = "violation"


class ViolationSeverity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"


class UserRole(str, Enum):
    admin = "admin"
    inspector = "inspector"
    supervisor = "supervisor"
    manufacturer = "manufacturer"
    consumer = "consumer"


class ReportType(str, Enum):
    summary = "summary"
    detailed = "detailed"
    violation = "violation"
    product = "product"
    audit = "audit"


class ReportFormat(str, Enum):
    pdf = "pdf"
    excel = "excel"
    csv = "csv"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class AuthVerifyRequest(BaseModel):
    token: str = Field(..., description="Supabase JWT access token")
    requested_role: Optional[UserRole] = None


class OTPRequest(BaseModel):
    mobile: str = Field(..., description="Mobile number in E.164 format, e.g. +919876543210")


class OTPVerifyRequest(BaseModel):
    mobile: str = Field(..., description="Mobile number in E.164 format")
    otp: str = Field(..., min_length=4, max_length=8, description="One-time password")
    requested_role: Optional[UserRole] = None


class AuthSessionResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Optional["UserResponse"] = None


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    user_id: Optional[str] = Field(None, min_length=3, max_length=80)
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    mobile: Optional[str] = None
    role: UserRole = UserRole.inspector
    organization: Optional[str] = None
    state: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    # Password is used when creating the Supabase auth user
    password: Optional[str] = Field(None, min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    mobile: Optional[str] = None
    role: Optional[UserRole] = None
    organization: Optional[str] = None
    state: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[str] = None
    supabase_user_id: Optional[str] = None
    role: UserRole
    name: str
    email: str
    mobile: Optional[str] = None
    organization: Optional[str] = None
    state: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Violations
# ---------------------------------------------------------------------------


class ViolationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    scan_id: Optional[UUID] = None
    rule_code: str
    field_name: str
    issue_description: str
    severity: ViolationSeverity
    legal_explanation: Optional[str] = None
    rag_context: Optional[str] = None
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------------


class ScanCreate(BaseModel):
    """Used internally; the router primarily accepts UploadFile."""
    product_name: Optional[str] = None
    brand: Optional[str] = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    product_name: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    compliance_result: ComplianceResult
    compliance_score: int = Field(..., ge=0, le=100)
    violations: List[Dict[str, Any]] = []
    rag_guidance: Optional[str] = None
    created_at: datetime


class ScanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_name: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    compliance_result: ComplianceResult
    compliance_score: int
    created_at: datetime


class ScanListResponse(BaseModel):
    items: List[ScanListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    brand: Optional[str] = None
    barcode: Optional[str] = None
    net_quantity: Optional[str] = None
    mrp: Optional[float] = Field(None, ge=0)
    mfr_date: Optional[str] = None
    exp_date: Optional[str] = None
    manufacturer_id: Optional[UUID] = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    barcode: Optional[str] = None
    name: str
    brand: Optional[str] = None
    manufacturer_id: Optional[UUID] = None
    net_quantity: Optional[str] = None
    mrp: Optional[float] = None
    mfr_date: Optional[str] = None
    exp_date: Optional[str] = None
    compliance_status: str
    scan_count: int
    last_scanned_at: Optional[datetime] = None
    created_at: datetime


class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    report_type: ReportType = ReportType.summary
    format: ReportFormat = ReportFormat.pdf
    # Optional filters: date_from, date_to, state, compliance_result, user_id …
    filters: Dict[str, Any] = {}


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    report_type: ReportType
    format: ReportFormat
    file_url: Optional[str] = None
    filters: Dict[str, Any] = {}
    created_at: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class ComplianceBreakdown(BaseModel):
    compliant: int = 0
    partial: int = 0
    violation: int = 0


class DashboardStats(BaseModel):
    total_scans: int = 0
    scans_today: int = 0
    compliance_rate: float = Field(0.0, ge=0, le=100)
    compliance_breakdown: ComplianceBreakdown = ComplianceBreakdown()
    total_violations: int = 0
    critical_violations: int = 0
    total_products: int = 0
    active_inspectors: int = 0
    recent_scans: List[ScanListItem] = []


class RecentViolation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scan_id: UUID
    rule_code: str
    field_name: str
    issue_description: str
    severity: ViolationSeverity
    created_at: datetime
    # Denormalised fields joined from scans / users
    product_name: Optional[str] = None
    inspector_name: Optional[str] = None
