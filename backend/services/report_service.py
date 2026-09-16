"""
Report generation service.

Produces PDF reports via ReportLab, Excel workbooks via openpyxl, and CSV via csv module.
"""

import csv
import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


# Compliance result colours
RESULT_COLOURS = {
    "compliant": colors.HexColor("#16a34a"),
    "partial": colors.HexColor("#d97706"),
    "violation": colors.HexColor("#dc2626"),
}

SEVERITY_COLOURS = {
    "critical": colors.HexColor("#dc2626"),
    "major": colors.HexColor("#d97706"),
    "minor": colors.HexColor("#2563eb"),
}


class ReportService:
    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def generate_pdf(
        self,
        title: str,
        scans: List[Dict[str, Any]],
        filters: Dict[str, Any],
        generated_by: str = "Legal Metrology System",
    ) -> bytes:
        """Generate a PDF compliance report and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        elements = []

        # ---------- Title block ----------
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=16,
            textColor=colors.HexColor("#1e3a5f"),
            spaceAfter=4,
        )
        elements.append(Paragraph(title, title_style))
        elements.append(
            Paragraph(
                f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')} "
                f"&nbsp;&nbsp;|&nbsp;&nbsp; By: {generated_by}",
                styles["Normal"],
            )
        )
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1e3a5f")))
        elements.append(Spacer(1, 0.4 * cm))

        # ---------- Applied filters ----------
        if filters:
            elements.append(Paragraph("Applied Filters", styles["Heading3"]))
            filter_text = "  |  ".join(f"{k}: {v}" for k, v in filters.items() if v)
            elements.append(Paragraph(filter_text or "None", styles["Normal"]))
            elements.append(Spacer(1, 0.3 * cm))

        # ---------- Summary statistics ----------
        total = len(scans)
        compliant = sum(1 for s in scans if s.get("compliance_result") == "compliant")
        partial = sum(1 for s in scans if s.get("compliance_result") == "partial")
        violation = sum(1 for s in scans if s.get("compliance_result") == "violation")
        avg_score = (
            round(sum(s.get("compliance_score", 0) for s in scans) / total, 1)
            if total
            else 0
        )

        summary_data = [
            ["Metric", "Value"],
            ["Total Scans", str(total)],
            ["Compliant", str(compliant)],
            ["Partial", str(partial)],
            ["Violation", str(violation)],
            ["Average Score", f"{avg_score} / 100"],
        ]
        summary_table = Table(summary_data, colWidths=[6 * cm, 4 * cm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
                ]
            )
        )
        elements.append(Paragraph("Summary", styles["Heading2"]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.5 * cm))

        # ---------- Scan detail table ----------
        if scans:
            elements.append(Paragraph("Scan Details", styles["Heading2"]))
            col_headers = ["Product", "Brand", "Score", "Result", "Date"]
            rows = [col_headers]
            for s in scans[:200]:  # cap at 200 rows for PDF
                result = s.get("compliance_result", "")
                rows.append(
                    [
                        s.get("product_name") or "—",
                        s.get("brand") or "—",
                        str(s.get("compliance_score", 0)),
                        result.upper(),
                        str(s.get("created_at", ""))[:10],
                    ]
                )

            detail_table = Table(
                rows,
                colWidths=[5 * cm, 4 * cm, 2 * cm, 3 * cm, 3 * cm],
                repeatRows=1,
            )
            detail_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("ALIGN", (2, 0), (3, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
            # Colour the Result column cells
            for row_idx, s in enumerate(scans[:200], start=1):
                result = s.get("compliance_result", "")
                colour = RESULT_COLOURS.get(result, colors.grey)
                detail_style.append(
                    ("TEXTCOLOR", (3, row_idx), (3, row_idx), colour)
                )
            detail_table.setStyle(TableStyle(detail_style))
            elements.append(detail_table)

        # ---------- Build ----------
        doc.build(elements)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Excel
    # ------------------------------------------------------------------

    def generate_excel(
        self,
        title: str,
        scans: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> bytes:
        """Generate an Excel compliance report and return as bytes."""
        wb = Workbook()

        # ----- Summary sheet -----
        ws_summary = wb.active
        ws_summary.title = "Summary"

        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
        alt_fill = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")

        ws_summary["A1"] = title
        ws_summary["A1"].font = Font(bold=True, size=14, color="1E3A5F")
        ws_summary["A2"] = (
            f"Generated: {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}"
        )
        ws_summary.append([])

        # Filters
        ws_summary.append(["Applied Filters"])
        ws_summary["A4"].font = Font(bold=True)
        for k, v in (filters or {}).items():
            if v:
                ws_summary.append([k, str(v)])

        ws_summary.append([])

        # Stats
        total = len(scans)
        compliant = sum(1 for s in scans if s.get("compliance_result") == "compliant")
        partial = sum(1 for s in scans if s.get("compliance_result") == "partial")
        violation_count = total - compliant - partial
        avg_score = (
            round(sum(s.get("compliance_score", 0) for s in scans) / total, 1)
            if total else 0
        )
        stats_row_start = ws_summary.max_row + 1
        stats = [
            ["Metric", "Value"],
            ["Total Scans", total],
            ["Compliant", compliant],
            ["Partial Compliance", partial],
            ["Violations", violation_count],
            ["Average Score", avg_score],
        ]
        for i, row in enumerate(stats):
            ws_summary.append(row)
            if i == 0:
                r = ws_summary.max_row
                for cell in ws_summary[r]:
                    cell.font = header_font
                    cell.fill = header_fill
            elif i % 2 == 0:
                for cell in ws_summary[ws_summary.max_row]:
                    cell.fill = alt_fill

        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 15

        # ----- Scans sheet -----
        ws_scans = wb.create_sheet("Scans")
        scan_headers = [
            "ID", "Product Name", "Brand", "Compliance Result",
            "Score", "Violations Count", "Date",
        ]
        ws_scans.append(scan_headers)
        for cell in ws_scans[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        result_fills = {
            "compliant": PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"),
            "partial": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
            "violation": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
        }

        for s in scans:
            violations_list = s.get("violations", []) or []
            row = [
                str(s.get("id", "")),
                s.get("product_name") or "",
                s.get("brand") or "",
                s.get("compliance_result", ""),
                s.get("compliance_score", 0),
                len(violations_list),
                str(s.get("created_at", ""))[:19],
            ]
            ws_scans.append(row)
            result = s.get("compliance_result", "")
            fill = result_fills.get(result)
            if fill:
                for cell in ws_scans[ws_scans.max_row]:
                    cell.fill = fill

        for col in ["A", "B", "C", "D", "E", "F", "G"]:
            ws_scans.column_dimensions[col].width = 20

        # ----- Violations sheet -----
        ws_violations = wb.create_sheet("Violations")
        viol_headers = [
            "Scan ID", "Rule Code", "Field", "Issue", "Severity", "Date",
        ]
        ws_violations.append(viol_headers)
        for cell in ws_violations[1]:
            cell.font = header_font
            cell.fill = header_fill

        for s in scans:
            violations_list = s.get("violations", []) or []
            for v in violations_list:
                ws_violations.append(
                    [
                        str(s.get("id", "")),
                        v.get("rule_code", ""),
                        v.get("field", ""),
                        v.get("issue", ""),
                        v.get("severity", ""),
                        str(s.get("created_at", ""))[:19],
                    ]
                )

        for col in ["A", "B", "C", "D", "E", "F"]:
            ws_violations.column_dimensions[col].width = 22

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()


    def generate_csv(
        self,
        title: str,
        scans: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(["LegalMetro Comply — Compliance Report"])
        writer.writerow(["Title", title])
        writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M IST")])
        if filters:
            for k, v in filters.items():
                if v:
                    writer.writerow([k.replace("_", " ").title(), str(v)])
        writer.writerow([])

        total = len(scans)
        compliant = sum(1 for s in scans if s.get("compliance_result") == "compliant")
        partial = sum(1 for s in scans if s.get("compliance_result") == "partial")
        violation = sum(1 for s in scans if s.get("compliance_result") == "violation")
        avg_score = (sum(s.get("compliance_score", 0) for s in scans) / total) if total else 0

        writer.writerow(["Summary"])
        writer.writerow(["Total Scans", total])
        writer.writerow(["Compliant", compliant])
        writer.writerow(["Partial", partial])
        writer.writerow(["Violations", violation])
        writer.writerow(["Average Score", f"{avg_score:.1f}"])
        writer.writerow([])

        writer.writerow(["Scan ID", "Product Name", "Brand", "Result", "Score", "Violations Count", "Inspector", "Date"])
        for s in scans:
            viols = s.get("violations") or []
            if isinstance(viols, str):
                import json
                try:
                    viols = json.loads(viols)
                except Exception:
                    viols = []
            writer.writerow([
                str(s.get("id", ""))[:8],
                s.get("product_name", ""),
                s.get("brand", ""),
                s.get("compliance_result", ""),
                s.get("compliance_score", 0),
                len(viols),
                s.get("inspector_name", ""),
                str(s.get("created_at", ""))[:19],
            ])

        return buffer.getvalue().encode("utf-8-sig")


report_service = ReportService()
