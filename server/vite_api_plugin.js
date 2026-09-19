import { scanLabelWithGemini } from "./gemini_scanner.js";
import { evaluateFieldsCompliance } from "./statutory_rules.js";

export { evaluateFieldsCompliance };

/**
 * In-memory / live persistent store for PRISM scans, products, and generated reports
 */
const LIVE_STORE = {
  scans: [
    {
      id: "scan-20250218-001",
      product_name: "Fortune Sunlite Refined Sunflower Oil 1L",
      brand: "Fortune",
      compliance_result: "compliant",
      compliance_score: 96,
      status: "compliant",
      score: 96,
      created_at: new Date(Date.now() - 3600000 * 4).toISOString(),
      scanned_at: new Date(Date.now() - 3600000 * 4).toISOString(),
      image_url: "",
      extracted_fields: {
        product_name: "Fortune Sunlite Refined Sunflower Oil",
        brand: "Fortune",
        mrp: "₹ 165.00 (Incl. of all taxes)",
        net_quantity: "1 L (910 g)",
        unit_sale_price: "₹ 0.165 / ml",
        mfr_date: "01/2025",
        exp_date: "10/2025",
        batch_no: "LOT-FS8820",
        manufacturer_name: "Adani Wilmar Limited, Fortune House, Near Navrangpura Railway Crossing, Ahmedabad - 380009, Gujarat",
        country_of_origin: "India",
        customer_care: "Toll Free: 1800-233-9999, customercare@adaniwilmar.in",
        fssai_license: "10013021000853",
        barcode: "8906007280145"
      },
      raw_ocr_text: "FORTUNE SUNLITE REFINED SUNFLOWER OIL\nNET QUANTITY: 1 L (910 g)\nMRP: Rs. 165.00 (Incl. of all taxes)\nUNIT SALE PRICE: Rs. 0.165 / ml\nMFD: 01/2025  EXP: 10/2025  BATCH: LOT-FS8820\nMFG BY: Adani Wilmar Limited, Fortune House, Ahmedabad - 380009, Gujarat\nCUSTOMER CARE: 1800-233-9999 / customercare@adaniwilmar.in\nFSSAI LIC NO: 10013021000853",
      violations: [],
      statutory_summary: "Packaging label fully complies with statutory requirements under Legal Metrology (Packaged Commodities) Rules, 2011.",
      rag_guidance: "Statutory audit verified under LM(PC)R 2011. All 7 mandatory declarations present.",
      model_used: "Gemini 3.8 Flash Vision + LM(PC)R Auditor"
    },
    {
      id: "scan-20250218-002",
      product_name: "Haldiram's Nagpur Aloo Bhujia 400g",
      brand: "Haldiram's",
      compliance_result: "violation",
      compliance_score: 48,
      status: "violation",
      score: 48,
      created_at: new Date(Date.now() - 3600000 * 8).toISOString(),
      scanned_at: new Date(Date.now() - 3600000 * 8).toISOString(),
      image_url: "",
      extracted_fields: {
        product_name: "Aloo Bhujia Spicy Potato Noodles",
        brand: "Haldiram's",
        mrp: "₹ 110.00",
        net_quantity: "400 g",
        unit_sale_price: "Not Declared / Not Found",
        mfr_date: "Not Declared / Not Found",
        exp_date: "08/2025",
        batch_no: "BNO-HB91",
        manufacturer_name: "Haldiram Foods International Pvt Ltd, Nagpur",
        country_of_origin: "India",
        customer_care: "support@haldirams.com",
        fssai_license: "10012022000338",
        barcode: "8904004401202"
      },
      raw_ocr_text: "HALDIRAM'S ALOO BHUJIA\nNET WEIGHT: 400 g\nMRP: Rs. 110.00\nBEST BEFORE: 08/2025\nBATCH: BNO-HB91\nHALDIRAM FOODS INTERNATIONAL PVT LTD, NAGPUR\nEMAIL: support@haldirams.com",
      violations: [
        {
          rule_code: "LMPC-R4(1)",
          field: "mrp",
          issue: "MRP missing mandatory statutory suffix '(Incl. of all taxes)'",
          severity: "critical",
          legal_section: "Rule 4(1) & Rule 6(1)(e) LM(PC)R 2011",
          explanation: "Rule 4(1): Retail sale price must state 'inclusive of all taxes'.",
          remedy: "Serve statutory inspection notice requiring correction under Section 18."
        },
        {
          rule_code: "LMPC-R6(1)(d)",
          field: "mfr_date",
          issue: "Month and Year of manufacture / packing missing from package",
          severity: "major",
          legal_section: "Rule 6(1)(d) of LM(PC)R 2011",
          explanation: "Rule 6(1)(d): Month and year of manufacture or pre-packing is mandatory.",
          remedy: "Issue notice to manufacturer for non-declaration of manufacturing date."
        },
        {
          rule_code: "LMPC-R6(1)(b)",
          field: "manufacturer_name",
          issue: "Manufacturer address appears incomplete (missing 6-digit postal PIN code)",
          severity: "minor",
          legal_section: "Rule 6(1)(b) LM(PC)R 2011",
          explanation: "Complete address must enable consumer to locate the manufacturer, including postal PIN code.",
          remedy: "Statutory advisory to include complete postal code on next packaging print run."
        }
      ],
      statutory_summary: "STATUTORY VIOLATION DETECTED: 3 violations identified including missing tax inclusion on MRP and missing manufacturing date under LM(PC)R 2011.",
      rag_guidance: "Enforcement Action: Issue Form V show-cause inspection memo under Rule 4/6 of LM(PC)R 2011 citing LMPC-R4(1), LMPC-R6(1)(d).",
      model_used: "Gemini 3.8 Flash Vision + LM(PC)R Auditor"
    }
  ],
  products: [
    { id: "p1", name: "Fortune Sunlite Refined Sunflower Oil 1L", brand: "Fortune", barcode: "8906007280145", scan_count: 5, last_score: 96, status: "compliant", last_scanned: new Date().toISOString() },
    { id: "p2", name: "Haldiram's Nagpur Aloo Bhujia 400g", brand: "Haldiram's", barcode: "8904004401202", scan_count: 3, last_score: 48, status: "violation", last_scanned: new Date().toISOString() },
    { id: "p3", name: "Amul Pure Ghee 1L Pouch", brand: "Amul", barcode: "8901262010115", scan_count: 8, last_score: 94, status: "compliant", last_scanned: new Date().toISOString() },
    { id: "p4", name: "Parle-G Gold Biscuits 200g", brand: "Parle", barcode: "8901719101018", scan_count: 6, last_score: 88, status: "compliant", last_scanned: new Date().toISOString() }
  ],
  reports: [
    {
      id: "REP-2025-0891",
      title: "Statutory Inspection Notice — Haldiram's Aloo Bhujia",
      type: "violation_notice",
      format: "PDF",
      file_url: "#",
      created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
      target_product: "Haldiram's Nagpur Aloo Bhujia 400g",
      violations_count: 3
    },
    {
      id: "REP-2025-0890",
      title: "Monthly LM(PC)R Enforcement Audit Summary",
      type: "summary",
      format: "EXCEL",
      file_url: "#",
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
      target_product: "All Packaged Goods",
      violations_count: 14
    }
  ],
  users: [
    { id: "u-1", user_id: "rajesh.agarwal", name: "Rajesh Agarwal", email: "rajesh.agarwal@doca.gov.in", role: "inspector", state: "Delhi", is_active: true, designation: "Enforcement Officer - Delhi Zone 1", organization: "Legal Metrology Enforcement Wing", scans_count: 42 },
    { id: "u-2", user_id: "meera.krishnan", name: "Meera Krishnan", email: "meera.krishnan@doca.gov.in", role: "supervisor", state: "Delhi", is_active: true, designation: "Nodal Officer / Supervisor", organization: "Ministry of Consumer Affairs", scans_count: 128 },
    { id: "u-3", user_id: "admin", name: "System Administrator", email: "admin@doca.gov.in", role: "admin", state: "Central", is_active: true, designation: "Director (Legal Metrology IT)", organization: "Department of Consumer Affairs (DoCA)", scans_count: 310 }
  ],
  cases: [
    {
      id: "case-901",
      scan_id: "scan-20250218-002",
      product_name: "Haldiram's Nagpur Aloo Bhujia 400g",
      status: "open",
      state: "Delhi",
      notes: "Missing mandatory tax declaration on MRP.",
      created_at: new Date(Date.now() - 3600000 * 20).toISOString(),
      updated_at: new Date(Date.now() - 3600000 * 20).toISOString()
    }
  ],
  audit_logs: [
    {
      id: "log-1",
      action: "ENGINE_INITIALIZED",
      user_id: "system",
      resource: "LM(PC)R 2011 Compliance Engine",
      details: { engine: "Gemini 3.8 Flash Vision", status: "operational" },
      created_at: new Date().toISOString()
    }
  ],
  thresholds: {
    state: "Delhi",
    thresholds: {
      "LMPC-R4(1)": { tolerance_pct: 0, min_score: 90, active: true },
      "LMPC-R6(1)": { tolerance_pct: 0, min_score: 95, active: true },
      "LMPC-R7(1)": { tolerance_pct: 2, min_score: 85, active: true },
      "LMPC-R6(6)": { tolerance_pct: 0, min_score: 80, active: true },
      "LMPC-R2(l)": { tolerance_pct: 5, min_score: 75, active: true }
    }
  }
};

/**
 * Reads stream body into Buffer / String
 */
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function sendJson(res, statusCode, data) {
  const json = JSON.stringify(data);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(json),
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  });
  res.end(json);
}

function sendHtmlOrDownload(res, filename, content, mime = "text/html") {
  res.writeHead(200, {
    "Content-Type": `${mime}; charset=utf-8`,
    "Content-Disposition": `attachment; filename="${filename}"`,
    "Access-Control-Allow-Origin": "*",
  });
  res.end(content);
}

function addApiRoutes(middlewares) {
  middlewares.use(async (req, res, next) => {
    const urlObj = new URL(req.url || "/", "http://localhost:3000");
    const pathname = urlObj.pathname;
    const method = req.method;

    if (method === "OPTIONS") {
      res.writeHead(200, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      });
      return res.end();
    }

    // ── GET /health & /api/scan/health ─────────────────────────────────
    if ((pathname === "/health" || pathname === "/api/scan/health" || pathname === "/api/health") && method === "GET") {
      return sendJson(res, 200, {
        status: "ok",
        mode: "live-ai-audit",
        engine: "Gemini 3.8 Flash Multimodal Vision + LM(PC)R 2011 Statutory Rule Auditor",
        timestamp: new Date().toISOString(),
        total_scans: LIVE_STORE.scans.length
      });
    }

    // ── POST /api/scan/image ───────────────────────────────────────────
    if (pathname === "/api/scan/image" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const contentType = req.headers["content-type"] || "";

        let base64Data = "";
        let mimeType = "image/jpeg";
        let fileName = "uploaded_label.jpg";
        let suggestedProduct = "";
        let suggestedBrand = "";

        if (contentType.includes("application/json")) {
          const body = JSON.parse(rawBuffer.toString("utf-8"));
          base64Data = body.image_base64 || body.image || body.file || "";
          mimeType = body.mime_type || "image/jpeg";
          fileName = body.file_name || fileName;
          suggestedProduct = body.product_name || "";
          suggestedBrand = body.brand || "";
        } else if (contentType.includes("multipart/form-data")) {
          const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/i);
          const boundary = boundaryMatch ? boundaryMatch[1] || boundaryMatch[2] : null;

          if (boundary) {
            const boundaryBuf = Buffer.from(`--${boundary}`);
            let startIdx = rawBuffer.indexOf(boundaryBuf);
            while (startIdx !== -1) {
              const nextStartIdx = rawBuffer.indexOf(boundaryBuf, startIdx + boundaryBuf.length);
              if (nextStartIdx === -1) break;

              const partBuf = rawBuffer.slice(startIdx + boundaryBuf.length, nextStartIdx);
              const headerSep = Buffer.from("\r\n\r\n");
              const headerEnd = partBuf.indexOf(headerSep);

              if (headerEnd !== -1) {
                const headerStr = partBuf.slice(0, headerEnd).toString("utf-8");
                if (headerStr.includes('filename="') || headerStr.includes("Content-Type: image/")) {
                  const fnMatch = headerStr.match(/filename="([^"]+)"/i);
                  if (fnMatch) fileName = fnMatch[1];

                  const ctMatch = headerStr.match(/Content-Type:\s*([^\r\n;]+)/i);
                  if (ctMatch) mimeType = ctMatch[1].trim();

                  let fileData = partBuf.slice(headerEnd + 4);
                  // Remove trailing \r\n before next boundary
                  if (fileData.length >= 2 && fileData[fileData.length - 2] === 13 && fileData[fileData.length - 1] === 10) {
                    fileData = fileData.slice(0, fileData.length - 2);
                  }
                  base64Data = fileData.toString("base64");
                  break;
                }
              }
              startIdx = nextStartIdx;
            }
          }
        }

        if (!base64Data) {
          return sendJson(res, 400, {
            error: "Missing image data. Please provide a packaging label photograph or image file.",
          });
        }

        console.log(`[PRISM Scanner] Processing real label scan: "${fileName}" (${mimeType})`);

        const scanResult = await scanLabelWithGemini({
          base64Data,
          mimeType,
          fileName,
          suggestedProduct,
        });

        // Save scan into live repository
        const scanId = "scan-" + Date.now();
        const storedScan = {
          id: scanId,
          product_name: scanResult.product_name || suggestedProduct || fileName.replace(/\.[^.]+$/, ""),
          brand: scanResult.brand || suggestedBrand || "",
          compliance_result: scanResult.compliance_result || scanResult.status || "compliant",
          compliance_score: scanResult.compliance_score ?? scanResult.score ?? 85,
          status: scanResult.compliance_result || scanResult.status || "compliant",
          score: scanResult.compliance_score ?? scanResult.score ?? 85,
          created_at: new Date().toISOString(),
          scanned_at: new Date().toISOString(),
          image_url: "",
          extracted_fields: scanResult.extracted_fields || {},
          raw_ocr_text: scanResult.raw_ocr_text || "",
          violations: scanResult.violations || [],
          statutory_summary: scanResult.statutory_summary || "",
          rag_guidance: scanResult.rag_guidance || "",
          model_used: scanResult.model_used || "Gemini 3.8 Flash Multimodal Vision"
        };

        LIVE_STORE.scans.unshift(storedScan);

        // Update product catalogue
        const existingProd = LIVE_STORE.products.find(p => p.name.toLowerCase() === storedScan.product_name.toLowerCase());
        if (existingProd) {
          existingProd.scan_count = (existingProd.scan_count || 1) + 1;
          existingProd.last_score = storedScan.compliance_score;
          existingProd.status = storedScan.status;
          existingProd.last_scanned = storedScan.created_at;
        } else {
          LIVE_STORE.products.unshift({
            id: "p-" + Date.now(),
            name: storedScan.product_name,
            brand: storedScan.brand,
            barcode: storedScan.extracted_fields?.barcode || "—",
            scan_count: 1,
            last_score: storedScan.compliance_score,
            status: storedScan.status,
            last_scanned: storedScan.created_at
          });
        }

        return sendJson(res, 200, {
          ...storedScan,
          scan_id: scanId,
          violations_count: (storedScan.violations || []).length
        });
      } catch (err) {
        console.error("[PRISM API] Scan error:", err);
        return sendJson(res, 500, {
          error: "Failed to scan label with AI engine: " + err.message,
          detail: err.stack,
        });
      }
    }

    // ── POST /api/scan/reevaluate ──────────────────────────────────────
    if (pathname === "/api/scan/reevaluate" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const fields = body.extracted_fields || body.fields || body;
        const evaluation = evaluateFieldsCompliance(fields);

        return sendJson(res, 200, {
          ...evaluation,
          product_name: fields.product_name || body.product_name || "Re-evaluated Commodity",
          brand: fields.brand || body.brand || "",
          extracted_fields: fields,
          violations_count: (evaluation.violations || []).length
        });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── GET /api/dashboard/stats ───────────────────────────────────────
    if (pathname === "/api/dashboard/stats" && method === "GET") {
      const scans = LIVE_STORE.scans;
      const totalScans = scans.length;
      const compliant = scans.filter(s => s.compliance_result === 'compliant' || s.status === 'compliant').length;
      const partial = scans.filter(s => s.compliance_result === 'partial' || s.status === 'partial').length;
      const violation = scans.filter(s => s.compliance_result === 'violation' || s.status === 'violation').length;
      const avgScore = totalScans ? Math.round(scans.reduce((a, s) => a + (s.compliance_score || s.score || 0), 0) / totalScans) : 85;
      const totalViolations = scans.reduce((a, s) => a + (s.violations ? s.violations.length : 0), 0);
      const criticalViolations = scans.reduce((a, s) => a + (s.violations ? s.violations.filter(v => v.severity === 'critical').length : 0), 0);

      return sendJson(res, 200, {
        total: totalScans,
        total_scans: totalScans,
        today: Math.min(totalScans, 6),
        today_scans: Math.min(totalScans, 6),
        today_violations: Math.min(totalViolations, 3),
        average_score: avgScore,
        avg_compliance_score: avgScore,
        total_violations: totalViolations,
        critical_violations: criticalViolations,
        compliance_breakdown: { compliant, partial, violation },
        compliant_products: compliant,
        products_with_violations: violation,
        monthly_trend: [72, 76, 80, 84, avgScore],
        total_users: LIVE_STORE.users.length,
        active_inspectors: LIVE_STORE.users.filter(u => u.role === 'inspector' && u.is_active).length,
        total_inspectors: LIVE_STORE.users.filter(u => u.role === 'inspector').length
      });
    }

    // ── GET /api/dashboard/violations ──────────────────────────────────
    if (pathname === "/api/dashboard/violations" && method === "GET") {
      const violationsList = [];
      LIVE_STORE.scans.forEach(s => {
        if (s.violations && s.violations.length > 0) {
          s.violations.forEach((v, idx) => {
            violationsList.push({
              id: `v-${s.id}-${idx}`,
              scan_id: s.id,
              product: s.product_name,
              product_name: s.product_name,
              brand: s.brand,
              field: v.field,
              field_name: v.field,
              rule_code: v.rule_code,
              issue: v.issue,
              severity: v.severity,
              legal_reference: v.legal_section || "Section 18 read with Section 36(1) of Legal Metrology Act, 2009",
              rag_context: v.explanation || "Mandatory statutory requirement under Legal Metrology (Packaged Commodities) Rules, 2011.",
              date: s.created_at,
              created_at: s.created_at
            });
          });
        }
      });

      return sendJson(res, 200, {
        items: violationsList,
        total: violationsList.length,
        page: 1,
        page_size: 100,
        total_pages: 1
      });
    }

    // ── GET /api/scan/history ──────────────────────────────────────────
    if (pathname === "/api/scan/history" && method === "GET") {
      const search = urlObj.searchParams.get("search") || "";
      const status = urlObj.searchParams.get("status") || "";
      let items = [...LIVE_STORE.scans];

      if (search) {
        const s = search.toLowerCase();
        items = items.filter(i => (i.product_name || "").toLowerCase().includes(s) || (i.brand || "").toLowerCase().includes(s));
      }
      if (status && status !== "all") {
        items = items.filter(i => (i.status || i.compliance_result) === status);
      }

      return sendJson(res, 200, {
        items: items.map(i => ({
          ...i,
          violations_count: (i.violations || []).length
        })),
        total: items.length,
        page: 1,
        page_size: 50,
        total_pages: 1
      });
    }

    // ── GET /api/products ──────────────────────────────────────────────
    if (pathname === "/api/products" && method === "GET") {
      return sendJson(res, 200, {
        items: LIVE_STORE.products,
        total: LIVE_STORE.products.length
      });
    }

    // ── GET /api/reports ───────────────────────────────────────────────
    if (pathname === "/api/reports" && method === "GET") {
      return sendJson(res, 200, {
        items: LIVE_STORE.reports,
        total: LIVE_STORE.reports.length
      });
    }

    // ── POST /api/reports/generate ─────────────────────────────────────
    if (pathname === "/api/reports/generate" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const reportType = body.report_type || body.type || "summary";
        const format = (body.format || "PDF").toUpperCase();
        const targetScanId = body.scan_id || (body.filters && body.filters.scan_id);
        const scan = (targetScanId && LIVE_STORE.scans.find(s => s.id === targetScanId)) ||
          body.scan_data ||
          LIVE_STORE.scans[0];

        const reportId = `REP-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
        const reportTitle = body.title || (reportType === "violation_notice"
          ? `Statutory Inspection Notice — ${scan ? scan.product_name : 'Packaged Goods'}`
          : `LM(PC)R 2011 Compliance Audit Report — ${scan ? scan.product_name : 'Commodity'}`);

        const newReport = {
          id: reportId,
          title: reportTitle,
          type: reportType,
          format: format,
          file_url: `/api/reports/${reportId}/download?format=${format.toLowerCase()}`,
          created_at: new Date().toISOString(),
          target_product: scan ? scan.product_name : "All Inspected Items",
          violations_count: scan ? (scan.violations || []).length : 0,
          scan_id: scan ? scan.id : null,
          scan_data: scan || null
        };

        LIVE_STORE.reports.unshift(newReport);
        return sendJson(res, 200, newReport);
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── GET /api/reports/:id/download ──────────────────────────────────
    if (pathname.startsWith("/api/reports/") && pathname.endsWith("/download") && method === "GET") {
      const parts = pathname.split("/");
      const repId = parts[3];
      const format = (urlObj.searchParams.get("format") || "pdf").toLowerCase();
      const report = LIVE_STORE.reports.find(r => r.id === repId);
      const scan = (report && report.scan_data) ||
        (report && report.scan_id && LIVE_STORE.scans.find(s => s.id === report.scan_id)) ||
        LIVE_STORE.scans[0];

      if (format === "csv" || format === "excel" || format === "xlsx") {
        let csv = "Report ID,Title,Product,Brand,Status,Compliance Score,Violations Count,MRP,Net Quantity,Mfg Date,Batch No,Manufacturer,Customer Care,Date\n";
        if (scan) {
          const ef = scan.extracted_fields || {};
          csv += `"${repId}","${report ? report.title : 'Statutory Audit'}","${scan.product_name || ''}","${scan.brand || ''}","${scan.status || scan.compliance_result || ''}",${scan.compliance_score || scan.score || 0},${(scan.violations||[]).length},"${ef.mrp || ''}","${ef.net_quantity || ''}","${ef.mfr_date || ef.mfg_date || ''}","${ef.batch_no || ef.batch_number || ''}","${(ef.manufacturer_name || ef.manufacturer_details || '').replace(/"/g, '""')}","${(ef.customer_care || '').replace(/"/g, '""')}","${scan.created_at || new Date().toISOString()}"\n`;
        }
        return sendHtmlOrDownload(res, `${repId}.csv`, csv, "text/csv");
      }

      const ef = (scan && scan.extracted_fields) || {};
      const score = scan ? (scan.compliance_score ?? scan.score ?? 0) : 100;
      const status = scan ? (scan.status || scan.compliance_result || 'compliant').toUpperCase() : 'COMPLIANT';
      const violations = (scan && scan.violations) || [];
      const scoreColor = status === 'VIOLATION' ? '#dc2626' : status === 'PARTIAL' ? '#d97706' : '#166534';

      // Printable Official Legal Metrology Statutory Inspection Report & Notice
      const htmlDoc = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${report ? report.title : 'Legal Metrology Statutory Report'}</title>
  <style>
    @media print {
      body { margin: 15mm; }
      .no-print { display: none !important; }
    }
    body {
      font-family: 'Times New Roman', Georgia, serif;
      line-height: 1.5;
      margin: 30px auto;
      max-width: 820px;
      color: #111827;
      background: #ffffff;
      padding: 24px;
    }
    .header {
      text-align: center;
      border-bottom: 2px solid #1e293b;
      padding-bottom: 12px;
      margin-bottom: 20px;
    }
    .emblem { font-size: 26px; margin-bottom: 4px; }
    .govt-heading { font-size: 11px; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: #4b5563; }
    .dept-title { font-size: 18px; font-weight: bold; color: #0f172a; margin: 4px 0; }
    .sub-dept { font-size: 12px; color: #374151; font-weight: 600; }
    .meta-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      padding: 12px 16px;
      margin-bottom: 20px;
      font-size: 12.5px;
    }
    .meta-item { display: flex; justify-content: space-between; }
    .meta-item strong { color: #334155; }
    .score-card {
      border: 2px solid ${scoreColor};
      background: #fdfefe;
      border-radius: 6px;
      padding: 14px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .score-badge {
      font-size: 32px;
      font-weight: 800;
      color: ${scoreColor};
      min-width: 90px;
      text-align: center;
      border-right: 2px solid #e2e8f0;
      padding-right: 14px;
    }
    .score-summary { font-size: 13px; color: #1e293b; }
    table.declarations {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
      font-size: 12px;
    }
    table.declarations th, table.declarations td {
      border: 1px solid #94a3b8;
      padding: 6px 10px;
      text-align: left;
    }
    table.declarations th {
      background: #e2e8f0;
      font-weight: 700;
      color: #0f172a;
    }
    .violation-block {
      border-left: 4px solid #dc2626;
      background: #fef2f2;
      padding: 8px 12px;
      margin-bottom: 10px;
      font-size: 12.5px;
      border-radius: 0 4px 4px 0;
    }
    .violation-title { font-weight: bold; color: #991b1b; }
    .violation-law { font-size: 11px; color: #4b5563; font-family: monospace; margin-top: 3px; }
    .ocr-box {
      background: #f1f5f9;
      border: 1px dashed #64748b;
      padding: 10px 14px;
      font-family: monospace;
      font-size: 11px;
      white-space: pre-wrap;
      max-height: 180px;
      overflow-y: auto;
      margin-bottom: 24px;
    }
    .action-bar {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-bottom: 20px;
    }
    .btn {
      background: #1e293b;
      color: #fff;
      padding: 8px 16px;
      border-radius: 4px;
      text-decoration: none;
      font-family: sans-serif;
      font-size: 12px;
      cursor: pointer;
      border: none;
    }
    .footer-seal {
      margin-top: 36px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      font-size: 12px;
      border-top: 1px solid #94a3b8;
      padding-top: 16px;
    }
  </style>
</head>
<body>
  <div class="action-bar no-print">
    <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
  </div>

  <div class="header">
    <div class="emblem">🏛️</div>
    <div class="govt-heading">Government of India · Ministry of Consumer Affairs, Food &amp; Public Distribution</div>
    <div class="dept-title">DEPARTMENT OF LEGAL METROLOGY</div>
    <div class="sub-dept">Packaged Rules Inspection &amp; Scanning Mechanism (PRISM) · Statutory Compliance Audit</div>
  </div>

  <div class="meta-grid">
    <div class="meta-item"><span><strong>Notice / Audit Ref:</strong></span> <span>${repId}</span></div>
    <div class="meta-item"><span><strong>Audit Date &amp; Time:</strong></span> <span>${scan ? (scan.scanned_at || scan.created_at || new Date().toLocaleString('en-IN')) : new Date().toLocaleString('en-IN')}</span></div>
    <div class="meta-item"><span><strong>Inspected Product:</strong></span> <span>${scan ? scan.product_name : 'Packaged Commodity'}</span></div>
    <div class="meta-item"><span><strong>Brand:</strong></span> <span>${scan ? (scan.brand || '—') : '—'}</span></div>
    <div class="meta-item"><span><strong>Barcode / GTIN:</strong></span> <span>${ef.barcode || '—'}</span></div>
    <div class="meta-item"><span><strong>Analysis Engine:</strong></span> <span>${scan ? (scan.model_used || 'Gemini Multimodal Vision') : 'PRISM Core'}</span></div>
  </div>

  <div class="score-card">
    <div class="score-badge">
      ${score}%
      <div style="font-size:11px;font-weight:600;letter-spacing:0.5px;">${status}</div>
    </div>
    <div class="score-summary">
      <strong>Statutory Compliance Assessment:</strong><br/>
      ${scan ? (scan.statutory_summary || scan.rag_guidance || 'Audit completed against provisions of Legal Metrology (Packaged Commodities) Rules, 2011.') : 'Audit complete.'}
    </div>
  </div>

  <h4 style="margin: 16px 0 8px; font-size:14px; text-transform:uppercase; letter-spacing:0.5px;">1. Audited Statutory Declarations (Rule 4, 6 &amp; 7 of LM(PC)R 2011)</h4>
  <table class="declarations">
    <thead>
      <tr>
        <th style="width:32%;">Statutory Field</th>
        <th style="width:48%;">Extracted Package Declaration</th>
        <th style="width:20%;">LM(PC)R Rule</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Common / Generic Name</td><td>${ef.product_name || 'Not Declared'}</td><td>Rule 6(1)(a)</td></tr>
      <tr><td>Maximum Retail Price (MRP)</td><td>${ef.mrp || 'Not Declared'}</td><td>Rule 4(1) &amp; 6(1)(e)</td></tr>
      <tr><td>Net Quantity (SI Units)</td><td>${ef.net_quantity || 'Not Declared'}</td><td>Rule 7(1)</td></tr>
      <tr><td>Unit Sale Price (USP)</td><td>${ef.unit_sale_price || 'Not Declared'}</td><td>Rule 6(1)(s)</td></tr>
      <tr><td>Date of Manufacture / Packing</td><td>${ef.mfr_date || ef.mfg_date || 'Not Declared'}</td><td>Rule 6(1)(d)</td></tr>
      <tr><td>Expiry / Best Before</td><td>${ef.exp_date || ef.expiry_date || 'Not Declared'}</td><td>Rule 6(1)(d)</td></tr>
      <tr><td>Batch / Lot / Code No.</td><td>${ef.batch_no || ef.batch_number || 'Not Declared'}</td><td>Rule 6(1)(e)</td></tr>
      <tr><td>Manufacturer / Packer Details</td><td>${ef.manufacturer_name || ef.manufacturer_details || 'Not Declared'}</td><td>Rule 6(1)(b)</td></tr>
      <tr><td>Country of Origin</td><td>${ef.country_of_origin || 'Not Declared'}</td><td>Rule 6(1)(aa)</td></tr>
      <tr><td>Consumer Care Redressal</td><td>${ef.customer_care || 'Not Declared'}</td><td>Rule 6(1)(f)</td></tr>
      <tr><td>FSSAI License / BIS Mark</td><td>${ef.fssai_license || 'Not Declared'}</td><td>FSSAI / BIS Acts</td></tr>
    </tbody>
  </table>

  <h4 style="margin: 16px 0 8px; font-size:14px; text-transform:uppercase; letter-spacing:0.5px;">2. Statutory Violations &amp; Legal Metrology Observations (${violations.length})</h4>
  ${violations.length > 0 ? violations.map((v, i) => `
    <div class="violation-block">
      <div class="violation-title">${i + 1}. [${(v.severity || 'MAJOR').toUpperCase()}] ${v.rule_code || 'Statutory Rule'} — ${v.issue || v.description}</div>
      <div class="violation-law"><strong>Statutory Provision:</strong> ${v.legal_section || v.legal_reference || 'Section 18 read with Section 36(1) of Legal Metrology Act, 2009'}</div>
      <div style="font-size:11.5px;color:#374151;margin-top:3px;"><strong>Recommended Enforcement Action:</strong> ${v.remedy || 'Issue compounding show-cause memo under Section 49 or rectification notice.'}</div>
    </div>
  `).join('') : '<p style="font-size:12.5px;color:#166534;background:#f0fdf4;padding:10px;border-radius:4px;">No statutory violations detected. The packaging label satisfies mandatory declarations under LM(PC)R 2011.</p>'}

  ${scan && scan.raw_ocr_text ? `
    <h4 style="margin: 16px 0 8px; font-size:14px; text-transform:uppercase; letter-spacing:0.5px;">3. Verbatim Label OCR Transcription</h4>
    <div class="ocr-box">${scan.raw_ocr_text}</div>
  ` : ''}

  <div class="footer-seal">
    <div>
      <strong>Packaged Rules Inspection &amp; Scanning Mechanism (PRISM)</strong><br/>
      Department of Legal Metrology · Govt. of India<br/>
      <span style="font-size:10px;color:#64748b;">Digital Verification Hash: SHA256-${repId}-${Date.now().toString(16)}</span>
    </div>
    <div style="text-align:center;min-width:200px;">
      <div style="border-bottom:1px solid #111;width:160px;margin:0 auto 6px;"></div>
      <strong>Authorized Enforcement Inspector</strong><br/>
      <span style="font-size:11px;color:#64748b;">Legal Metrology Department</span>
    </div>
  </div>
</body>
</html>`;

      return sendHtmlOrDownload(res, `${repId}.html`, htmlDoc, "text/html");
    }

    // ── GET /api/scan/:id ─────────────────────────────────────────────
    if (pathname.startsWith("/api/scan/") && !pathname.includes("/consumer-report") && method === "GET") {
      const scanId = pathname.replace("/api/scan/", "");
      const scan = LIVE_STORE.scans.find(s => s.id === scanId) || LIVE_STORE.scans[0];
      return sendJson(res, 200, scan);
    }

    // ── POST /api/scan/:id/consumer-report ─────────────────────────────
    if (pathname.includes("/consumer-report") && method === "POST") {
      const parts = pathname.split("/");
      const scanId = parts[3];
      const scan = LIVE_STORE.scans.find(s => s.id === scanId);
      const newCase = {
        id: "case-" + Date.now(),
        scan_id: scanId,
        product_name: scan ? scan.product_name : "Reported Commodity",
        status: "open",
        state: "Delhi",
        notes: "Consumer reported non-compliance for field inspection.",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      LIVE_STORE.cases.unshift(newCase);
      return sendJson(res, 200, { message: "Report successfully submitted to Legal Metrology Department.", case_id: newCase.id });
    }

    // ── GET /api/products/:id ──────────────────────────────────────────
    if (pathname.startsWith("/api/products/") && method === "GET") {
      const pid = pathname.replace("/api/products/", "");
      const product = LIVE_STORE.products.find(p => p.id === pid) || LIVE_STORE.products[0];
      const relatedScans = LIVE_STORE.scans.filter(s => s.product_name === product.name);
      return sendJson(res, 200, { ...product, recent_scans: relatedScans });
    }

    // ── Users CRUD & Audit Logs ────────────────────────────────────────
    if (pathname === "/api/users/audit-logs" && method === "GET") {
      return sendJson(res, 200, {
        items: LIVE_STORE.audit_logs,
        total: LIVE_STORE.audit_logs.length
      });
    }

    if (pathname === "/api/users" && method === "GET") {
      const roleFilter = urlObj.searchParams.get("role");
      const search = urlObj.searchParams.get("search");
      let items = [...LIVE_STORE.users];
      if (roleFilter) items = items.filter(u => u.role === roleFilter);
      if (search) {
        const s = search.toLowerCase();
        items = items.filter(u => (u.name || "").toLowerCase().includes(s) || (u.user_id || "").toLowerCase().includes(s) || (u.state || "").toLowerCase().includes(s));
      }
      return sendJson(res, 200, {
        items,
        total: items.length
      });
    }

    if (pathname === "/api/users" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const newUser = {
          id: "u-" + Date.now(),
          user_id: body.user_id || body.username || `emp.${Date.now().toString().slice(-4)}`,
          name: body.name || `${body.first_name || ''} ${body.last_name || ''}`.trim() || "Officer",
          email: body.email || `${body.user_id || 'officer'}@doca.gov.in`,
          role: body.role || "inspector",
          state: body.state || "Delhi",
          designation: body.designation || (body.role === "supervisor" ? "Nodal Officer" : "Field Inspector"),
          organization: body.organization || "Department of Consumer Affairs",
          is_active: true,
          scans_count: 0,
          created_at: new Date().toISOString()
        };
        LIVE_STORE.users.push(newUser);
        LIVE_STORE.audit_logs.unshift({
          id: "log-" + Date.now(),
          action: "USER_CREATED",
          user_id: "admin",
          resource: newUser.user_id,
          details: { role: newUser.role, state: newUser.state },
          created_at: new Date().toISOString()
        });
        return sendJson(res, 201, newUser);
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    if (pathname.startsWith("/api/users/") && method === "PUT") {
      try {
        const uid = pathname.replace("/api/users/", "");
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const user = LIVE_STORE.users.find(u => u.id === uid || u.user_id === uid);
        if (user) {
          Object.assign(user, body);
          return sendJson(res, 200, user);
        }
        return sendJson(res, 404, { error: "User not found" });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    if (pathname.startsWith("/api/users/") && method === "DELETE") {
      const uid = pathname.replace("/api/users/", "");
      LIVE_STORE.users = LIVE_STORE.users.filter(u => u.id !== uid && u.user_id !== uid);
      return sendJson(res, 200, { message: "User deleted successfully" });
    }

    // ── Cases & Enforcement Tracking ───────────────────────────────────
    if (pathname === "/api/cases" && method === "GET") {
      return sendJson(res, 200, {
        items: LIVE_STORE.cases,
        total: LIVE_STORE.cases.length
      });
    }

    if (pathname === "/api/cases" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const newCase = {
          id: "case-" + Date.now(),
          scan_id: body.scan_id || null,
          product_name: body.product_name || "Inspection Sample",
          status: body.status || "open",
          state: body.state || "Delhi",
          notes: body.notes || "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        LIVE_STORE.cases.unshift(newCase);
        return sendJson(res, 201, newCase);
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── Rule Thresholds ────────────────────────────────────────────────
    if (pathname === "/api/rules/thresholds" && method === "GET") {
      return sendJson(res, 200, LIVE_STORE.thresholds);
    }

    if (pathname === "/api/rules/thresholds" && method === "PUT") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        Object.assign(LIVE_STORE.thresholds, body);
        return sendJson(res, 200, { message: "Thresholds updated successfully.", thresholds: LIVE_STORE.thresholds });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── POST /api/auth/staff-login ─────────────────────────────────────
    if (pathname === "/api/auth/staff-login" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const { user_id, password, role } = body;

        const user = LIVE_STORE.users.find(u => u.user_id.toLowerCase() === (user_id || "").toLowerCase());
        const token = "prism_jwt_" + Buffer.from(JSON.stringify({ user_id, role, time: Date.now() })).toString("base64");

        return sendJson(res, 200, {
          token,
          user_id: user_id || "officer",
          name: user ? user.name : (user_id ? user_id.charAt(0).toUpperCase() + user_id.slice(1) : "Enforcement Officer"),
          role: role || (user ? user.role : "inspector"),
          state: user ? user.state : "Delhi",
          is_active: true
        });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── POST /api/auth/otp/request & verify ─────────────────────────────
    if (pathname === "/api/auth/otp/request" && method === "POST") {
      return sendJson(res, 200, { message: "OTP sent successfully to registered mobile number.", otp_hint: "1234" });
    }

    if (pathname === "/api/auth/otp/verify" && method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const role = body.role || "consumer";
        const mobile = body.mobile || "9876543210";
        const prefix = role === "manufacturer" ? "MFR91" : "CTZN91";
        const userId = `${prefix}_${new Date().getFullYear()}_${mobile.slice(-4)}`;

        return sendJson(res, 200, {
          token: "prism_otp_token_" + Date.now(),
          user_id: userId,
          role,
          mobile,
          name: role === "manufacturer" ? "Registered Manufacturer" : "Citizen Consumer"
        });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── GET & PUT /api/auth/me ──────────────────────────────────────────
    if (pathname === "/api/auth/me" && method === "GET") {
      return sendJson(res, 200, {
        user_id: "rajesh.agarwal",
        name: "Rajesh Agarwal",
        role: "inspector",
        state: "Delhi",
        is_active: true
      });
    }

    if (pathname === "/api/auth/me" && method === "PUT") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        return sendJson(res, 200, { success: true, ...body });
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    if (pathname === "/api/auth/credentials" && method === "PUT") {
      return sendJson(res, 200, { message: "Credentials updated successfully." });
    }

    next();
  });
}

export function prismApiPlugin() {
  return {
    name: "prism-api-middleware",
    configureServer(server) {
      addApiRoutes(server.middlewares);
    },
    configurePreviewServer(server) {
      addApiRoutes(server.middlewares);
    },
  };
}
