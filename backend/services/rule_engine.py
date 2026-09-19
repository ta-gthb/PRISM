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

    # Strict metric unit symbols for pre-press artwork (Rule 7(2) strictly mandates 'g', 'kg', 'ml', 'l')
    STRICT_METRIC_INVALID_PATTERN = re.compile(
        r"\d+\s*(?:gms|gm|g\.|kilos|ltr|ltrs|mls)\b",
        re.IGNORECASE,
    )

    # Rule 6(10) Mandatory Declarations for E-Commerce Digital Listings
    ECOMMERCE_MANDATORY_FIELDS: List[tuple] = [
        ("manufacturer_name", "LMPC-R6(10)-MFR", "critical",
         "Rule 6(10): Digital listing must prominently display name & complete address of the manufacturer, packer, or importer."),
        ("net_quantity", "LMPC-R6(10)-NETQTY", "critical",
         "Rule 6(10): Net quantity in standard metric units must be explicitly stated on the digital marketplace product page."),
        ("mrp", "LMPC-R6(10)-MRP", "critical",
         "Rule 6(10): Maximum Retail Price inclusive of all taxes must be declared on the digital listing prior to consumer purchase."),
        ("country_of_origin", "LMPC-R6(10)-ORIGIN", "major",
         "Rule 6(10) & Consumer Protection Rules 2020: Country of Origin must be displayed conspicuously on digital product listings."),
        ("customer_care", "LMPC-R6(10)-CARE", "minor",
         "Rule 6(10): Consumer care contact details (telephone number or e-mail address) must be displayed on product listing."),
    ]

    def run(
        self,
        fields: Dict[str, Any],
        analysis: Dict[str, Any] | None = None,
        state: str | None = None,
        input_type: str = "physical_package",
    ) -> Dict[str, Any]:
        """
        Execute rule checks against *fields* according to inspection input_type:
        - 'physical_package': On-pack declarations, physical image legibility, batch/mfr date.
        - 'artwork_design': Pre-press artwork proofs, PDP font sizes, strict metric symbols ('g'/'ml'), contrast.
        - 'ecommerce_listing': Rule 6(10) digital marketplace declarations, seller disclosure, country of origin.
        """
        violations: List[RuleViolation] = []
        analysis = analysis or {}
        input_type = (input_type or "physical_package").lower()

        # ------------------------------------------------------------------
        # E-Commerce Product Listing Inspection (Rule 6(10))
        # ------------------------------------------------------------------
        if input_type == "ecommerce_listing":
            for field, rule_code, severity, explanation in self.ECOMMERCE_MANDATORY_FIELDS:
                value = fields.get(field, "")
                if not value or not str(value).strip():
                    violations.append(
                        RuleViolation(
                            rule_code=rule_code,
                            field=field,
                            issue=f"Digital listing missing mandatory {field.replace('_', ' ')} under Rule 6(10)",
                            severity=severity,
                            explanation=explanation,
                        )
                    )

            # Check net quantity format on e-commerce listing
            nq = str(fields.get("net_quantity", "")).strip()
            if nq and not self.METRIC_UNITS_PATTERN.search(nq):
                violations.append(
                    RuleViolation(
                        rule_code="LMPC-R6(10)-UNITS",
                        field="net_quantity",
                        issue="E-commerce net quantity not stated in standard metric units (kg/g/l/ml)",
                        severity="major",
                        explanation="Rule 6(10) & Rule 7(2): Digital listings must state net content using standard metric units.",
                    )
                )

            # Check MRP format
            mrp = str(fields.get("mrp", "")).strip()
            if mrp and not self.MRP_VALUE_PATTERN.match(mrp.replace(" ", "").replace("₹", "").replace("Rs", "").replace("Rs.", "")):
                violations.append(
                    RuleViolation(
                        rule_code="LMPC-R6(10)-PRICE",
                        field="mrp",
                        issue="E-commerce listing price format ambiguous or invalid",
                        severity="major",
                        explanation="Rule 6(10): Digital price must clearly indicate MRP inclusive of all taxes.",
                    )
                )

            total_checks = len(self.ECOMMERCE_MANDATORY_FIELDS) + 2

        # ------------------------------------------------------------------
        # Packaging Artwork / Design File Inspection (Pre-Press Verification)
        # ------------------------------------------------------------------
        elif input_type == "artwork_design":
            # Check mandatory declarations for packaging artwork proofs
            for field, rule_code, severity in self.MANDATORY_FIELDS:
                value = fields.get(field, "")
                # On artwork proofs, batch number and mfr date are often placeholder keylines like "BATCH: B### MFD: MM/YY"
                if field in ("batch_no", "mfr_date"):
                    if not value or not str(value).strip():
                        violations.append(
                            RuleViolation(
                                rule_code=rule_code,
                                field=field,
                                issue=f"Packaging artwork missing placeholder/keyline for {field.replace('_', ' ')}",
                                severity="minor",
                                explanation=f"Pre-print proof must allocate clear print window/keyline for {field.replace('_', ' ')} under Rule 6.",
                            )
                        )
                    continue

                if not value or not str(value).strip():
                    violations.append(
                        RuleViolation(
                            rule_code=rule_code,
                            field=field,
                            issue=f"Packaging artwork missing mandatory {field.replace('_', ' ')} on layout",
                            severity=severity,
                            explanation=self.EXPLANATIONS.get(field, ""),
                        )
                    )

            # Pre-press typography & unit symbol check: e.g. 'gms' is strictly forbidden under Rule 7(2)
            nq = str(fields.get("net_quantity", "")).strip()
            if nq:
                if self.STRICT_METRIC_INVALID_PATTERN.search(nq):
                    violations.append(
                        RuleViolation(
                            rule_code="LMPC-ARTWORK-R7(2)",
                            field="net_quantity",
                            issue="Non-standard metric symbol on artwork (use 'g' or 'kg', not 'gm' / 'gms')",
                            severity="major",
                            explanation="Rule 7(2) Pre-Press: The abbreviations 'gm', 'gms', 'ltr', 'mls' are non-compliant. Only standard symbols 'g', 'kg', 'l', 'ml' are permissible.",
                        )
                    )
                elif not self.METRIC_UNITS_PATTERN.search(nq):
                    violations.append(
                        RuleViolation(
                            rule_code="LMPC-R7(2)",
                            field="net_quantity",
                            issue="Net quantity not expressed in standard metric units on artwork",
                            severity="major",
                            explanation="Rule 7(2): Net quantity must use metric units on the artwork layout.",
                        )
                    )

            # Check MRP declaration wording on artwork proof
            mrp_text = str(fields.get("mrp", "")).lower()
            if mrp_text and "incl" not in mrp_text and "tax" not in mrp_text and not fields.get("mrp_inclusive_taxes", True):
                violations.append(
                    RuleViolation(
                        rule_code="LMPC-ARTWORK-R4",
                        field="mrp",
                        issue="Artwork MRP block missing mandatory 'incl. of all taxes' declaration",
                        severity="major",
                        explanation="Rule 4(1): Pre-press artwork must explicitly include the words 'inclusive of all taxes' or 'incl. of all taxes'.",
                    )
                )

            total_checks = len(self.MANDATORY_FIELDS) + 2

        # ------------------------------------------------------------------
        # Physical Package Image Inspection (Standard Physical Label)
        # ------------------------------------------------------------------
        else:
            for field, rule_code, severity in self.MANDATORY_FIELDS:
                value = fields.get(field, "")
                if not value or not str(value).strip():
                    violations.append(
                        RuleViolation(
                            rule_code=rule_code,
                            field=field,
                            issue=f"{field.replace('_', ' ').title()} not found on physical label",
                            severity=severity,
                            explanation=self.EXPLANATIONS.get(field, ""),
                        )
                    )

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

            mrp = str(fields.get("mrp", "")).strip()
            if mrp and not self.MRP_VALUE_PATTERN.match(mrp.replace(" ", "").replace("₹", "").replace("Rs", "").replace("Rs.", "")):
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

            readability = float(analysis.get("readability_score", 0))
            text_height = int(analysis.get("median_text_height_px", 0))
            if readability < 55 or text_height < 8:
                violations.append(RuleViolation(
                    rule_code="LMPC-READABILITY", field="label_readability",
                    issue="Label declarations are not reliably legible in the submitted image",
                    severity="major",
                    explanation="Mandatory declarations must be conspicuous and legible. Retake a sharp, front-facing image or use larger label text.",
                ))

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
            "input_type": input_type,
            "violations": [asdict(v) for v in violations],
            "compliance_score": score,
            "compliance_result": status,
            "artwork_clearance": "ready_for_print" if (critical_count == 0 and major_count == 0) else "revision_required",
            "summary": {
                "total_checks": total_checks,
                "passed": max(0, total_checks - len(violations)),
                "failed": len(violations),
                "critical": critical_count,
                "major": major_count,
                "minor": minor_count,
            },
        }


rule_engine = LMPCRuleEngine()
