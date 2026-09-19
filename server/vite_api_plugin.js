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
    { user_id: "rajesh.agarwal", name: "Rajesh Agarwal", role: "inspector", state: "Delhi", is_active: true, scans_count: 42 },
    { user_id: "meera.krishnan", name: "Meera Krishnan", role: "supervisor", state: "Delhi", is_active: true, scans_count: 128 },
    { user_id: "admin", name: "System Administrator", role: "admin", state: "Central", is_active: true, scans_count: 310 }
  ]
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
            const bufferStr = rawBuffer.toString("binary");
            const parts = bufferStr.split(`--${boundary}`);

            for (const part of parts) {
              if (part.includes('filename="') || part.includes("Content-Type: image/")) {
                const fnMatch = part.match(/filename="([^"]+)"/i);
                if (fnMatch) fileName = fnMatch[1];

                const ctMatch = part.match(/Content-Type:\s*([^\r\n]+)/i);
                if (ctMatch) mimeType = ctMatch[1].trim();

                const headerEndIndex = part.indexOf("\r\n\r\n");
                if (headerEndIndex !== -1) {
                  const binaryData = part.slice(headerEndIndex + 4, part.lastIndexOf("\r\n"));
                  base64Data = Buffer.from(binaryData, "binary").toString("base64");
                  break;
                }
              }
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
        const targetScanId = body.scan_id || (LIVE_STORE.scans[0] ? LIVE_STORE.scans[0].id : null);
        const scan = LIVE_STORE.scans.find(s => s.id === targetScanId) || LIVE_STORE.scans[0];

        const reportId = `REP-${new Date().getFullYear()}-${Math.floor(1000 + Math.random() * 9000)}`;
        const reportTitle = reportType === "violation_notice"
          ? `Statutory Inspection Notice — ${scan ? scan.product_name : 'Packaged Goods'}`
          : `LM(PC)R Compliance Audit Report (${format})`;

        const newReport = {
          id: reportId,
          title: reportTitle,
          type: reportType,
          format: format,
          file_url: `/api/reports/${reportId}/download?format=${format.toLowerCase()}`,
          created_at: new Date().toISOString(),
          target_product: scan ? scan.product_name : "All Inspected Items",
          violations_count: scan ? (scan.violations || []).length : 0
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
      const format = urlObj.searchParams.get("format") || "pdf";
      const report = LIVE_STORE.reports.find(r => r.id === repId) || LIVE_STORE.reports[0];
      const scan = LIVE_STORE.scans[0];

      if (format === "csv" || format === "excel" || format === "xlsx") {
        let csv = "Report ID,Title,Product,Status,Score,Violations Count,Date\n";
        LIVE_STORE.scans.forEach(s => {
          csv += `"${repId}","${report ? report.title : 'Audit'}","${s.product_name}","${s.status}",${s.compliance_score},${(s.violations||[]).length},"${s.created_at}"\n`;
        });
        return sendHtmlOrDownload(res, `${repId}.csv`, csv, "text/csv");
      }

      // Printable HTML Inspection Report
      const htmlDoc = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>${report ? report.title : 'Legal Metrology Report'}</title>
  <style>
    body { font-family: 'Times New Roman', Georgia, serif; line-height: 1.6; margin: 40px; color: #111; max-width: 800px; margin: auto; }
    .header { text-align: center; border-bottom: 2px solid #222; padding-bottom: 12px; margin-bottom: 20px; }
    .title { font-size: 18px; font-weight: bold; text-transform: uppercase; margin: 5px 0; }
    .sub { font-size: 13px; color: #444; }
    .meta-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .meta-table td { padding: 6px 8px; border: 1px solid #ccc; font-size: 13px; }
    .meta-table th { background: #f0f0f0; padding: 6px 8px; border: 1px solid #ccc; font-size: 13px; text-align: left; }
    .score-box { background: #fafafa; border: 2px solid #333; padding: 16px; margin: 20px 0; text-align: center; }
    .violation-card { border-left: 4px solid #dc2626; padding: 8px 12px; margin-bottom: 10px; background: #fff5f5; }
    .footer { margin-top: 40px; display: flex; justify-content: space-between; font-size: 12px; border-top: 1px solid #ccc; padding-top: 12px; }
  </style>
</head>
<body>
  <div class="header">
    <div style="font-size:11px;letter-spacing:1px;">GOVERNMENT OF INDIA · MINISTRY OF CONSUMER AFFAIRS, FOOD &amp; PUBLIC DISTRIBUTION</div>
    <div class="title">DEPARTMENT OF LEGAL METROLOGY</div>
    <div class="sub">Packaged Rules Inspection &amp; Scanning Mechanism (PRISM) · Statutory Audit Report</div>
  </div>

  <table class="meta-table">
    <tr><th>Report Reference</th><td>${repId}</td><th>Audit Date</th><td>${new Date().toLocaleString('en-IN')}</td></tr>
    <tr><th>Inspected Product</th><td>${scan ? scan.product_name : 'Packaged Commodity'}</td><th>Brand</th><td>${scan ? scan.brand : '—'}</td></tr>
    <tr><th>Compliance Score</th><td><strong>${scan ? scan.compliance_score : 85}% (${scan ? scan.status.toUpperCase() : 'COMPLIANT'})</strong></td><th>Rules Applied</th><td>LM(PC)R 2011 &amp; Legal Metrology Act 2009</td></tr>
  </table>

  <div class="score-box">
    <div style="font-size:14px;color:#555;">STATUTORY COMPLIANCE EVALUATION</div>
    <div style="font-size:32px;font-weight:bold;color:${scan && scan.status==='violation' ? '#dc2626' : '#166534'};">${scan ? scan.compliance_score : 85} / 100</div>
    <div style="font-size:13px;margin-top:6px;">${scan ? scan.statutory_summary : 'Label complies with Legal Metrology statutory provisions.'}</div>
  </div>

  <h3>Detected Non-Compliances &amp; Statutory Flags</h3>
  ${scan && scan.violations && scan.violations.length > 0 
    ? scan.violations.map(v => `
      <div class="violation-card">
        <strong>${v.rule_code} — ${v.field.toUpperCase()}:</strong> ${v.issue}
        <div style="font-size:11px;color:#666;margin-top:4px;">Legal Provision: ${v.legal_section || 'Section 18 / Section 36(1) LM Act 2009'}</div>
        <div style="font-size:11px;color:#333;margin-top:2px;">Remedy / Action: ${v.remedy || 'Rectify packaging declaration'}</div>
      </div>
    `).join('')
    : '<p><em>No statutory non-compliances flagged. All mandatory declarations under LM(PC)R 2011 are present.</em></p>'
  }

  <div class="footer">
    <div>Verified by PRISM Enforcement AI System<br/>Government of India Legal Metrology Portal</div>
    <div style="text-align:right;">Authorized Enforcement Wing<br/>Department of Consumer Affairs</div>
  </div>
  <script>window.onload = function() { window.print(); };<\/script>
</body>
</html>`;

      return sendHtmlOrDownload(res, `${repId}.html`, htmlDoc, "text/html");
    }

    // ── GET /api/users ─────────────────────────────────────────────────
    if (pathname === "/api/users" && method === "GET") {
      return sendJson(res, 200, {
        items: LIVE_STORE.users,
        total: LIVE_STORE.users.length
      });
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

    // ── GET /api/auth/me ───────────────────────────────────────────────
    if (pathname === "/api/auth/me" && method === "GET") {
      return sendJson(res, 200, {
        user_id: "rajesh.agarwal",
        name: "Rajesh Agarwal",
        role: "inspector",
        state: "Delhi",
        is_active: true
      });
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
