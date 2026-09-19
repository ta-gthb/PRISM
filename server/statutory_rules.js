/**
 * Legal Metrology (Packaged Commodities) Rules, 2011 (LM(PC)R 2011)
 * Statutory Compliance Rule Auditor & Evaluator
 */

export function evaluateFieldsCompliance(fields = {}) {
  const violations = [];
  let score = 100;

  const mrp = (fields.mrp || "").toLowerCase();
  const netQty = (fields.net_quantity || "").toLowerCase();
  const mfrDate = (fields.mfr_date || "").toLowerCase();
  const mfrName = (fields.manufacturer_name || "").toLowerCase();
  const care = (fields.customer_care || "").toLowerCase();
  const origin = (fields.country_of_origin || "").toLowerCase();
  const prodName = (fields.product_name || "").trim();
  const brand = (fields.brand || "").trim();
  const batchNo = (fields.batch_no || "").trim().toLowerCase();
  const usp = (fields.unit_sale_price || "").trim().toLowerCase();

  // Rule 6(1)(a) - Generic product name
  if (!prodName || prodName.includes("not declared") || prodName.includes("not found")) {
    score -= 20;
    violations.push({
      rule_code: "LMPC-R6(1)(a)",
      field: "product_name",
      issue: "Generic or common name of the commodity is missing from label",
      severity: "critical",
      legal_section: "Section 18 & Section 36(1) of Legal Metrology Act, 2009",
      explanation: "Rule 6(1)(a): The common or generic name of the commodity must be declared on every package.",
      remedy: "Issue notice under Section 18 for misbranded/unlabeled packaged commodity."
    });
  }

  // Rule 4(1) - MRP must state "inclusive of all taxes"
  if (!mrp || mrp.includes("not declared") || mrp.includes("not found")) {
    score -= 25;
    violations.push({
      rule_code: "LMPC-R4(1)",
      field: "mrp",
      issue: "Maximum Retail Price (MRP) not declared on the package",
      severity: "critical",
      legal_section: "Section 18 / Section 36(1) of Legal Metrology Act, 2009",
      explanation: "Rule 4(1): Retail sale price (MRP) is mandatory on all pre-packaged commodities.",
      remedy: "Compound offence under Section 49 or issue seizure memo for unregistered retail sale."
    });
  } else if (!mrp.includes("incl") && !mrp.includes("tax")) {
    score -= 20;
    violations.push({
      rule_code: "LMPC-R4(1)",
      field: "mrp",
      issue: "MRP missing mandatory statutory suffix '(Incl. of all taxes)'",
      severity: "critical",
      legal_section: "Rule 4(1) & Rule 6(1)(e) LM(PC)R 2011",
      explanation: "Rule 4(1): The retail sale price must state 'inclusive of all taxes' or '(Incl. of all taxes)'.",
      remedy: "Serve statutory inspection notice requiring correction of packaging artwork within 15 days."
    });
  }

  // Rule 7(1) - Net quantity standard SI metric units
  const metricRegex = /\b(\d+(\.\d+)?)\s*(g|kg|ml|l|ltr|litre|litres|gram|grams|kilogram|m|cm|units?|pieces?|nos?|n)\b/i;
  const nonMetricRegex = /\b(fl\.?\s*oz|fluid\s*ounces?|oz|ounces?|lbs?|pounds?|feet|ft|inches|in)\b/i;

  if (!netQty || netQty.includes("not declared") || netQty.includes("not found")) {
    score -= 25;
    violations.push({
      rule_code: "LMPC-R7(1)",
      field: "net_quantity",
      issue: "Net quantity statement not declared on principal display panel",
      severity: "critical",
      legal_section: "Section 18 & Section 36(1) of Legal Metrology Act, 2009",
      explanation: "Rule 7(1): Net quantity declaration is mandatory on every pre-packaged commodity.",
      remedy: "Issue immediate compounding show-cause notice."
    });
  } else if (nonMetricRegex.test(netQty) && !metricRegex.test(netQty)) {
    score -= 25;
    violations.push({
      rule_code: "LMPC-R7(1)",
      field: "net_quantity",
      issue: "Net quantity declared in non-metric units (e.g. fluid ounces/pounds) without standard metric unit",
      severity: "critical",
      legal_section: "Section 18 / Section 36(1) of Legal Metrology Act, 2009",
      explanation: "Rule 7(1): Net quantity must be in standard SI metric units (g, kg, ml, L). Non-metric units are prohibited.",
      remedy: "Seizure of non-standard packaged goods under Section 15 of Legal Metrology Act."
    });
  }

  // Rule 6(1)(d) - Month & Year of manufacture / packing
  if (!mfrDate || mfrDate.includes("not declared") || mfrDate.includes("not found")) {
    score -= 15;
    violations.push({
      rule_code: "LMPC-R6(1)(d)",
      field: "mfr_date",
      issue: "Month and Year of manufacture, packing, or import missing from package",
      severity: "major",
      legal_section: "Rule 6(1)(d) of LM(PC)R 2011",
      explanation: "Rule 6(1)(d): Month and year of manufacture or pre-packing is mandatory.",
      remedy: "Issue notice to manufacturer for non-declaration of manufacturing date."
    });
  }

  // Rule 6(1)(b) - Manufacturer name and address
  if (!mfrName || mfrName.includes("not declared") || mfrName.includes("not found")) {
    score -= 20;
    violations.push({
      rule_code: "LMPC-R6(1)(b)",
      field: "manufacturer_name",
      issue: "Complete manufacturer / packer postal address missing",
      severity: "critical",
      legal_section: "Rule 6(1)(b) LM(PC)R 2011",
      explanation: "Rule 6(1)(b): Name and complete postal address of the manufacturer or packer must be stated.",
      remedy: "Seizure and show-cause notice under Section 18 of Legal Metrology Act."
    });
  } else if (!mfrName.match(/\b\d{6}\b/) && !mfrName.includes("pin") && !mfrName.includes("postal")) {
    score -= 8;
    violations.push({
      rule_code: "LMPC-R6(1)(b)",
      field: "manufacturer_name",
      issue: "Manufacturer address appears incomplete (missing 6-digit postal PIN code)",
      severity: "minor",
      legal_section: "Rule 6(1)(b) LM(PC)R 2011 & Landmark Supreme Court Judgments",
      explanation: "Rule 6(1)(b): Complete address must enable consumer to locate the manufacturer, including postal PIN code.",
      remedy: "Statutory advisory to include complete postal code on next packaging print run."
    });
  }

  // Rule 6(1)(f) - Consumer care contact
  if (!care || care.includes("not declared") || care.includes("not found")) {
    score -= 15;
    violations.push({
      rule_code: "LMPC-R6(1)(f)",
      field: "customer_care",
      issue: "Consumer care details (phone, email, or designation) not provided",
      severity: "major",
      legal_section: "Rule 6(1)(f) and Rule 2(l) of LM(PC)R 2011",
      explanation: "Rule 6(1)(f): Name, address, telephone number and email address of person/office to contact in case of consumer complaints.",
      remedy: "Serve compliance notice under Rule 6(1)(f)."
    });
  } else if (!care.includes("@") && !care.match(/\b\d{10}\b/) && !care.match(/1800[-\s]?\d{3}[-\s]?\d{3,4}/)) {
    score -= 8;
    violations.push({
      rule_code: "LMPC-R6(1)(f)",
      field: "customer_care",
      issue: "Consumer care missing valid phone number or email address",
      severity: "minor",
      legal_section: "Rule 6(1)(f) LM(PC)R 2011",
      explanation: "Mandatory declaration must contain functional telephone number and email ID.",
      remedy: "Advise rectification on packaging label."
    });
  }

  // Rule 6(1)(aa) - Country of origin for imported goods
  if (origin.includes("not declared") || origin.includes("not found")) {
    if (mfrName.includes("import") || prodName.includes("import") || origin.includes("violat")) {
      score -= 20;
      violations.push({
        rule_code: "LMPC-R6(1)(aa)",
        field: "country_of_origin",
        issue: "Country of Origin not declared on imported pre-packaged commodity",
        severity: "critical",
        legal_section: "Rule 6(1)(aa) of LM(PC)R 2011 (Mandatory for all imported goods)",
        explanation: "Rule 6(1)(aa): Name of the country of origin or manufacture or assembly shall be mentioned on the package.",
        remedy: "Immediate compounding or stop-sale notice under Section 18 of the Legal Metrology Act."
      });
    }
  }

  // Rule 6(1)(e) - Batch number
  if (!batchNo || batchNo.includes("not declared") || batchNo.includes("not found")) {
    score -= 5;
    violations.push({
      rule_code: "LMPC-R6(1)(e)",
      field: "batch_no",
      issue: "Batch, lot, or code number not identifiable on package",
      severity: "minor",
      legal_section: "Rule 6(1)(e) LM(PC)R 2011",
      explanation: "Batch number is required to identify manufacturing lot for traceability.",
      remedy: "Inspection advisory for lot traceability compliance."
    });
  }

  score = Math.max(0, Math.min(100, score));

  let status = "compliant";
  if (score < 60 || violations.some(v => v.severity === "critical")) {
    status = "violation";
  } else if (score < 85 || violations.length > 0) {
    status = "partial";
  }

  let statutorySummary = "";
  if (status === "compliant") {
    statutorySummary = `Packaging label complies with statutory requirements under Legal Metrology (Packaged Commodities) Rules, 2011. Key declarations including MRP (with tax inclusion), Metric Net Quantity, Month/Year of Packaging, Manufacturer Address, and Consumer Care are satisfactorily declared.`;
  } else if (status === "partial") {
    statutorySummary = `Label partially conforms to LM(PC)R 2011 with ${violations.length} non-critical observation(s). Rectification advised for packaging compliance.`;
  } else {
    statutorySummary = `STATUTORY VIOLATION DETECTED: The packaging label violates mandatory requirements of the Legal Metrology Act, 2009 and LM(PC)R 2011. ${violations.length} violation(s) identified including critical omissions. Formal statutory notice under Section 18 / Section 36 warranted.`;
  }

  return {
    score,
    compliance_score: score,
    status,
    compliance_result: status,
    violations,
    statutory_summary: statutorySummary,
    rag_guidance: violations.length > 0
      ? `Enforcement Action: Issue Form V show-cause inspection memo under Rule 4/6/7 of LM(PC)R 2011 citing ${violations.map(v => v.rule_code).join(", ")}.`
      : `Packaging label meets statutory standards under LM(PC)R 2011.`
  };
}
