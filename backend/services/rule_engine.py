"""
Rule engine for Legal Metrology (Packaged Commodities) Rules, 2011.

Checks extracted label fields and returns a structured compliance report
containing individual violations, a numeric score (0-100), and a status
string (compliant / partial / violation).
"""

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class RuleViolation:
    rule_code: str
    field: str
    issue: str
    severity: str  # critical | major | minor
    explanation: str


class LMPCRuleEngine:
    """
    Implements checks for mandatory declarations on pre-packaged commodities
    as required by LM (PC) Rules, 2011 (amended).
    """

    # (field_name, rule_code, severity)
    MANDATORY_FIELDS: List[tuple] = [
        ("manufacturer_name", "LMPC-R6(1)", "critical"),
        ("net_quantity", "LMPC-R7(1)", "critical"),
        ("mrp", "LMPC-R4(1)", "critical"),
        ("mfr_date", "LMPC-R6(6)", "major"),
        ("customer_care", "LMPC-R2(l)", "minor"),
        ("country_of_origin", "LMPC-R6(2)", "major"),
        ("batch_no", "LMPC-R6(5)", "minor"),
    ]

    EXPLANATIONS: Dict[str, str] = {
        "manufacturer_name": (
            "Rule 6(1): Name and complete address of manufacturer, packer or "
            "importer must appear on every package."
        ),
        "net_quantity": (
            "Rule 7(1): Net quantity in standard units of weights and measures "
            "must be declared on every package."
        ),
        "mrp": (
            "Rule 4(1): Maximum Retail Price inclusive of all taxes must be "
            "declared. Prefix 'MRP' or 'Maximum Retail Price' is mandatory."
        ),
        "mfr_date": (
            "Rule 6(6): Month and year of manufacture, packing or import must "
            "be indicated on the label."
        ),
        "customer_care": (
            "Rule 2(l): Consumer care details (name, address and telephone "
            "number or e-mail) must be present."
        ),
        "country_of_origin": (
            "Rule 6(2): Country of origin or manufacture must be stated for "
            "imported packaged commodities."
        ),
        "batch_no": (
            "Rule 6(5): Batch number, lot number or code number identifying "
            "the production lot must be declared."
        ),
    }

    # Standard metric unit abbreviations accepted by Rule 7(2)
    METRIC_UNITS_PATTERN = re.compile(
        r"\d+\s*(?:kg|g|gm|gram|kilogram|l|litre|liter|ml|millilitre|milliliter|no\.?|nos\.?|pcs\.?|pack)",
        re.IGNORECASE,
    )

    # Valid MRP numeral (may include commas and decimal)
    MRP_VALUE_PATTERN = re.compile(r"^[\d,]+(?:\.\d{1,2})?$")

    def run(self, fields: Dict[str, Any], analysis: Dict[str, Any] | None = None, state: str | None = None) -> Dict[str, Any]:
        """
        Execute all rule checks against *fields* (dict from OCR / form data).
        Applies state-specific rule threshold values if set for the jurisdiction.

        Returns
        -------
        dict with keys:
            violations       : list of dicts (one per rule violation)
            compliance_score : int 0-100
            compliance_result: "compliant" | "partial" | "violation"
            summary          : dict with counts
        """
        violations: List[RuleViolation] = []
        analysis = analysis or {}

        # ------------------------------------------------------------------
        # 1. Mandatory field presence
        # ------------------------------------------------------------------
        for field, rule_code, severity in self.MANDATORY_FIELDS:
            value = fields.get(field, "")
            if not value or not str(value).strip():
                violations.append(
                    RuleViolation(
                        rule_code=rule_code,
                        field=field,
                        issue=f"{field.replace('_', ' ').title()} not found on label",
                        severity=severity,
                        explanation=self.EXPLANATIONS.get(field, ""),
                    )
                )

        # ------------------------------------------------------------------
        # 2. Net quantity must be in metric units  — Rule 7(2)
        # ------------------------------------------------------------------
        nq = str(fields.get("net_quantity", "")).strip()
        if nq and not self.METRIC_UNITS_PATTERN.search(nq):
            violations.append(
                RuleViolation(
                    rule_code="LMPC-R7(2)",
                    field="net_quantity",
                    issue="Net quantity not expressed in standard metric units (kg/g/l/ml)",
                    severity="major",
                    explanation=(
                        "Rule 7(2): Net quantity must be declared in the metric "
                        "system — kilograms (kg), grams (g), litres (l), or "
                        "millilitres (ml) as applicable."
                    ),
                )
            )

        # ------------------------------------------------------------------
        # 3. MRP must be a valid numeral  — Rule 4(2)
        # ------------------------------------------------------------------
        mrp = str(fields.get("mrp", "")).strip()
        if mrp and not self.MRP_VALUE_PATTERN.match(mrp.replace(" ", "")):
            violations.append(
                RuleViolation(
                    rule_code="LMPC-R4(2)",
                    field="mrp",
                    issue="MRP value is not a valid numeral or is illegible",
                    severity="major",
                    explanation=(
                        "Rule 4(2): MRP must be stated as a numeral inclusive of "
                        "all taxes; it must be clearly legible."
                    ),
                )
            )

        # ------------------------------------------------------------------
        # 4. FSSAI licence number (14-digit) for food items  — FSS Act
        #    Treat as a minor advisory when detected as present but malformed.
        # ------------------------------------------------------------------
        fssai = str(fields.get("fssai_no", "")).strip()
        if fssai and not re.fullmatch(r"[0-9]{14}", fssai):
            violations.append(
                RuleViolation(
                    rule_code="FSSAI-LIC",
                    field="fssai_no",
                    issue="FSSAI licence number detected but does not match 14-digit format",
                    severity="minor",
                    explanation=(
                        "FSSAI Licence Number must be exactly 14 digits as per "
                        "Food Safety and Standards Act, 2006."
                    ),
                )
            )

        readability = float(analysis.get("readability_score", 0))
        text_height = int(analysis.get("median_text_height_px", 0))
        if readability < 55 or text_height < 8:
            violations.append(RuleViolation(
                rule_code="LMPC-READABILITY", field="label_readability",
                issue="Label declarations are not reliably legible in the submitted image",
                severity="major",
                explanation="Mandatory declarations must be conspicuous and legible. Retake a sharp, front-facing image or use larger label text.",
            ))
        # ------------------------------------------------------------------
        # 5. Score computation
        # ------------------------------------------------------------------
        #  Total possible checks = mandatory fields + 3 format checks
        total_checks = len(self.MANDATORY_FIELDS) + 3

        critical_count = sum(1 for v in violations if v.severity == "critical")
        major_count = sum(1 for v in violations if v.severity == "major")
        minor_count = sum(1 for v in violations if v.severity == "minor")

        # Weighted deduction: critical 15 pts, major 8 pts, minor 3 pts
        deductions = critical_count * 15 + major_count * 8 + minor_count * 3
        score = max(0, 100 - deductions)

        # Threshold defaults: compliant >= 90, partial >= 60, violation < 60
        compliant_threshold = 90
        partial_threshold = 60
        critical_threshold = 40

        if state:
            try:
                from db.connection import get_db_connection
                conn = get_db_connection()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT critical_threshold, major_threshold, auto_flag_below FROM state_rule_thresholds WHERE state = %s", (state,))
                    row = cur.fetchone()
                    if row:
                        critical_threshold = row.get("critical_threshold", 40)
                        compliant_threshold = row.get("major_threshold", 65)
                        partial_threshold = row.get("auto_flag_below", 50)
                finally:
                    conn.close()
            except Exception:
                pass

        if score >= compliant_threshold:
            status = "compliant"
        elif score >= partial_threshold:
            status = "partial"
        else:
            status = "violation"

        return {
            "violations": [asdict(v) for v in violations],
            "compliance_score": score,
            "compliance_result": status,
            "summary": {
                "total_checks": total_checks,
                "passed": total_checks - len(violations),
                "failed": len(violations),
                "critical": critical_count,
                "major": major_count,
                "minor": minor_count,
            },
        }


rule_engine = LMPCRuleEngine()
