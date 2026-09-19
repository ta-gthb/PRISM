"""
Pydantic v2 schemas for PRISM (Packaged Rules Inspection & Scanning Mechanism).

All response models use model_config = ConfigDict(from_attributes=True) so
they can be constructed directly from psycopg2 RealDict rows.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _parse_flexible_datetime(v: Any) -> Any:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        s = v.strip()
        # Normalise two-digit postgres timezone offset like '+00' or '-05' to '+00:00' or '-05:00'
        s = re.sub(r"([+-]\d{2})$", r"\1:00", s)
        try:
            return datetime.fromisoformat(s)
        except Exception:
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
        ):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return s
    return v


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


class StaffLoginRequest(BaseModel):
    user_id: str = Field(..., min_length=3, max_length=80)
    password: str = Field(..., min_length=8)
    role: UserRole


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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization: Optional[str] = None
    state: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    # Password is used when creating the Supabase auth user
    password: Optional[str] = Field(None, min_length=8)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    role: Optional[UserRole] = None
    organization: Optional[str] = None
    state: Optional[str] = None
    designation: Optional[str] = None
    gstin: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class AdminCredentialsUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    current_password: str = Field(..., min_length=1, description="Mandatory current password for identity verification")


class RuleThresholdsUpdate(BaseModel):
    critical_threshold: int = Field(..., ge=0, le=100)
    major_threshold: int = Field(..., ge=0, le=100)
    auto_flag_below: int = Field(..., ge=0, le=100)


class RuleThresholdsResponse(BaseModel):
    state: str
    critical_threshold: int
    major_threshold: int
    auto_flag_below: int
    updated_at: Optional[datetime] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    organization: Optional[str] = Field(None, max_length=250)
    gstin: Optional[str] = Field(None, pattern=r"^[0-9A-Z]{15}$")


class ConsumerCaseUpdate(BaseModel):
    status: str = Field(..., pattern=r"^(open|under_review|resolved|closed)$")
    notes: Optional[str] = Field(None, max_length=2000)


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
    is_active: bool = True
    created_at: Optional[Union[datetime, str]] = None
    updated_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _val_user_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


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
    created_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _val_violation_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


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
    input_type: Optional[str] = "physical_package"
    extracted_fields: Dict[str, Any] = {}
    compliance_result: ComplianceResult
    compliance_score: int = Field(..., ge=0, le=100)
    violations: List[Dict[str, Any]] = []
    rag_guidance: Optional[str] = None
    evidence: List[Dict[str, Any]] = []
    created_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _val_scan_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


class ScanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_name: Optional[str] = None
    brand: Optional[str] = None
    image_url: Optional[str] = None
    input_type: Optional[str] = "physical_package"
    compliance_result: ComplianceResult
    compliance_score: int
    created_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _val_item_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


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
    last_scanned_at: Optional[Union[datetime, str]] = None
    created_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", "last_scanned_at", mode="before")
    @classmethod
    def _val_prod_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


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
    created_at: Optional[Union[datetime, str]] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _val_rep_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)


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
    created_at: Optional[Union[datetime, str]] = None
    # Denormalised fields joined from scans / users
    product_name: Optional[str] = None
    inspector_name: Optional[str] = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _val_rec_dates(cls, v: Any) -> Any:
        return _parse_flexible_datetime(v)
