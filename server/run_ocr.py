#!/usr/bin/env python3
"""
PRISM Deep Learning OCR & Legal Metrology Inspection Runner.
Executes PaddleOCR (with OpenCV preprocessing and Tesseract fallback),
extracts mandatory packaging fields under LM(PC)R 2011, runs rule checks,
and outputs pure JSON for the application server.
"""

import sys
import os
import json
import base64

# Add backend directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from services.ocr_service import ocr_service
    from services.rule_engine import rule_engine
    from services.rag_service import rag_service
except ImportError as e:
    sys.stderr.write(f"Import error: {e}\n")
    sys.exit(1)


def process_image_payload(image_bytes: bytes, product_name: str = "", brand: str = ""):
    if not image_bytes:
        return {
            "error": "Empty image payload",
            "compliance_result": "violation",
            "compliance_score": 0,
            "raw_ocr_text": "Error: Empty image bytes provided.",
            "extracted_fields": {},
            "violations": [],
        }

    # 1. Run real deep-learning OCR (PaddleOCR or Tesseract)
    try:
        ocr_result = ocr_service.process_image(image_bytes)
    except Exception as exc:
        return {
            "error": f"OCR processing failed: {exc}",
            "compliance_result": "violation",
            "compliance_score": 0,
            "raw_ocr_text": f"OCR Error: {exc}",
            "extracted_fields": {},
            "violations": [],
        }

    raw_text = ocr_result.get("raw_text", "").strip()
    extracted_fields = ocr_result.get("fields", {}) or {}
    analysis = ocr_result.get("analysis", {}) or {}

    # Override product/brand if provided by user/form
    if product_name and product_name.strip():
        extracted_fields["product_name"] = product_name.strip()
    elif not extracted_fields.get("product_name"):
        # If product name wasn't detected, use the first non-empty line of text
        lines = [l.strip() for l in raw_text.splitlines() if len(l.strip()) > 2]
        if lines:
            extracted_fields["product_name"] = lines[0]
        else:
            extracted_fields["product_name"] = "Unidentified Commodity"

    if brand and brand.strip():
        extracted_fields["brand"] = brand.strip()
    elif not extracted_fields.get("brand"):
        extracted_fields["brand"] = extracted_fields.get("product_name", "Unbranded")

    # If absolutely no text was detected on the label
    if not raw_text or len(raw_text) < 3:
        violations = [
            {
                "rule_code": "LMPC-R6(1)",
                "field": "label_declarations",
                "issue": "No legible text or mandatory packaging declarations detected",
                "severity": "critical",
                "explanation": "Rule 6: Packaging label must bear clear, legible mandatory declarations in standard lettering.",
                "rag_context": "Mandatory declarations under LM(PC)R 2011 require conspicuous, legible printing on the principal display panel."
            }
        ]
        return {
            "product_name": extracted_fields.get("product_name", "Unidentified Commodity"),
            "brand": extracted_fields.get("brand", "Unbranded"),
            "compliance_result": "violation",
            "compliance_score": 0,
            "status": "violation",
            "score": 0,
            "extracted_fields": extracted_fields,
            "raw_ocr_text": "No readable text detected on this packaging image. Please verify lighting, focus, or upload a higher resolution photo.",
            "violations": violations,
            "violations_count": len(violations),
            "statutory_summary": "Zero mandatory declarations detected. Label fails statutory legibility and declaration requirements under LM(PC)R 2011.",
            "rag_guidance": "Clear declarations of MRP, Net Quantity, Manufacturer details, and Manufacturing Date are legally mandatory.",
            "model_used": analysis.get("engine", "PaddleOCR Deep Learning + Tesseract OCR"),
            "ocr_analysis": analysis,
        }

    # 2. Run LM(PC)R 2011 statutory rule engine
    compliance = rule_engine.run(extracted_fields, analysis)
    violations = compliance.get("violations", [])

    # 3. Augment violations with RAG legal context
    for v in violations:
        v["rag_context"] = rag_service.explain_violation(
            v.get("rule_code", ""),
            v.get("field", ""),
            v.get("issue", ""),
        )

    rag_guidance = rag_service.get_compliance_guidance(violations)
    engine_name = analysis.get("engine", "PaddleOCR Deep Learning / Tesseract OCR")

    # Generate statutory summary based on actual violations
    if not violations:
        statutory_summary = f"Packaging label complies with statutory requirements under Legal Metrology (Packaged Commodities) Rules, 2011. Key declarations including MRP, Net Quantity, Date of Packing, and Manufacturer details were successfully recognized. (Audited via {engine_name})."
    else:
        critical_count = sum(1 for v in violations if v.get("severity") == "critical")
        statutory_summary = f"Detected {len(violations)} statutory violation(s) ({critical_count} critical) under Legal Metrology (Packaged Commodities) Rules, 2011. (Audited via {engine_name})."

    return {
        "product_name": extracted_fields.get("product_name"),
        "brand": extracted_fields.get("brand"),
        "compliance_result": compliance.get("compliance_result", "violation"),
        "compliance_score": compliance.get("compliance_score", 0),
        "status": compliance.get("compliance_result", "violation"),
        "score": compliance.get("compliance_score", 0),
        "extracted_fields": extracted_fields,
        "raw_ocr_text": raw_text,
        "violations": violations,
        "violations_count": len(violations),
        "statutory_summary": statutory_summary,
        "rag_guidance": rag_guidance,
        "model_used": engine_name,
        "ocr_analysis": analysis,
    }


def main():
    if len(sys.argv) < 2:
        # Read from stdin as JSON: {"image_base64": "...", "product_name": "...", "brand": "..."}
        raw_input = sys.stdin.read()
        try:
            payload = json.loads(raw_input)
            img_b64 = payload.get("image_base64") or payload.get("file") or ""
            if "," in img_b64:
                img_b64 = img_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(img_b64)
            prod = payload.get("product_name", "")
            brand = payload.get("brand", "")
        except Exception as e:
            print(json.dumps({"error": f"Invalid JSON stdin: {e}"}))
            sys.exit(1)
    else:
        file_path = sys.argv[1]
        prod = sys.argv[2] if len(sys.argv) > 2 else ""
        brand = sys.argv[3] if len(sys.argv) > 3 else ""
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            print(json.dumps({"error": f"Failed to read file {file_path}: {e}"}))
            sys.exit(1)

    result = process_image_payload(img_bytes, prod, brand)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
