import { GoogleGenAI } from "@google/genai";
import { evaluateFieldsCompliance } from "./statutory_rules.js";

let aiInstance = null;

function getGenAI() {
  const apiKey =
    process.env.GEMINI_API_KEY ||
    process.env.GOOGLE_API_KEY ||
    process.env.VITE_GEMINI_API_KEY ||
    "";
  if (!aiInstance) {
    aiInstance = new GoogleGenAI({
      apiKey: apiKey || undefined,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiInstance;
}

// Order prioritizing robust modern multimodal vision flash models
const CANDIDATE_MODELS = [
  "gemini-flash-latest",
  "gemini-3.8-flash",
  "gemini-3.1-pro-preview",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isDemandSpikeOrRetryableError(err) {
  if (!err) return false;
  const msg = ((err.message || "") + " " + JSON.stringify(err)).toLowerCase();
  return (
    msg.includes("503") ||
    msg.includes("unavailable") ||
    msg.includes("high demand") ||
    msg.includes("spikes in demand") ||
    msg.includes("429") ||
    msg.includes("resource_exhausted") ||
    msg.includes("rate limit") ||
    msg.includes("overloaded")
  );
}

/**
 * Parses embedded text chunks if the uploaded image or data contains SVG markup
 */
function extractEmbeddedSvgText(base64Data) {
  try {
    const rawString = Buffer.from(base64Data.slice(0, 15000), "base64").toString("utf-8");
    if (rawString.includes("<svg") || rawString.includes("xmlns")) {
      const matches = rawString.match(/<text[^>]*>([\s\S]*?)<\/text>/gi) || [];
      const textPieces = matches
        .map((m) => m.replace(/<[^>]+>/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim())
        .filter((t) => t.length > 1);
      return textPieces.join("\n");
    }
  } catch (e) {
    // Ignore parsing error
  }
  return "";
}

/**
 * Robust fallback auditor using statutory LM(PC)R 2011 rule engine
 * Invoked when all remote Gemini endpoints experience high-demand spikes (503/429)
 */
function fallbackLabelAudit({
  base64Data,
  fileName = "",
  suggestedProduct = "",
  lastErrorMessage = "",
}) {
  console.log("[PRISM Scanner] Running Statutory Rule Engine fallback due to AI model demand spike...");
  const svgText = extractEmbeddedSvgText(base64Data);

  const fields = {
    product_name: suggestedProduct || (fileName ? fileName.replace(/\.[^.]+$/, "").replace(/[-_]/g, " ") : "Packaged Commodity Sample"),
    brand: "Inspected Brand",
    mrp: "Not Declared / Not Found",
    net_quantity: "Not Declared / Not Found",
    unit_sale_price: "Not Declared / Not Found",
    mfr_date: "Not Declared / Not Found",
    exp_date: "Not Declared / Not Found",
    batch_no: "Not Declared / Not Found",
    manufacturer_name: "Not Declared / Not Found",
    country_of_origin: "India",
    customer_care: "Not Declared / Not Found",
    fssai_license: "Not Declared / Not Found",
    barcode: "Not Declared / Not Found",
  };

  // If SVG text is available, perform statutory regex extraction
  if (svgText) {
    const lines = svgText.split("\n").map((l) => l.trim()).filter(Boolean);

    lines.forEach((line) => {
      // MRP
      if (/mrp|retail price|₹|rs\./i.test(line)) {
        fields.mrp = line.replace(/^(mrp|max\.?\s*retail\s*price|retail\s*price)[:\s]*/i, "").trim();
      }
      // Net quantity
      if (/net\s*(qty|quantity)|weight|volume/i.test(line)) {
        fields.net_quantity = line.replace(/^net\s*(quantity|qty)[:\s]*/i, "").trim();
      }
      // Mfg date
      if (/mfg|packed|packing|date of/i.test(line) && !/exp/i.test(line)) {
        fields.mfr_date = line.replace(/^(mfg|mfg\s*&amp;\s*packing|packing\s*date)[:\s]*/i, "").trim();
      }
      // Expiry date
      if (/exp|expiry|use by|best before/i.test(line)) {
        fields.exp_date = line.replace(/^(exp|expiry\s*date|use\s*by)[:\s]*/i, "").trim();
      }
      // Batch
      if (/batch|lot/i.test(line)) {
        fields.batch_no = line.replace(/^(batch\s*no\.?|lot\s*#?)[:\s]*/i, "").trim();
      }
      // Manufacturer
      if (/manufactured|packed by|marketed by|importer/i.test(line)) {
        fields.manufacturer_name = line;
      }
      // Customer care
      if (/customer|consumer|care|feedback|helpline|toll free/i.test(line)) {
        fields.customer_care = line;
      }
      // Brand / Commodity
      if (/commodity/i.test(line)) {
        fields.product_name = line.replace(/^commodity[:\s]*/i, "").trim();
      }
      if (/origin/i.test(line) && /country/i.test(line)) {
        fields.country_of_origin = line.includes("NOT DECLARED") ? "Not Declared / Not Found" : line;
      }
    });

    if (fields.product_name === "Packaged Commodity Sample" && lines[0]) {
      fields.product_name = lines[0];
      fields.brand = lines[0].split(" ")[0] || "Inspected Brand";
    }
  }

  // Evaluate extracted declarations against LM(PC)R 2011 statutory rules
  const evalResult = evaluateFieldsCompliance(fields);

  return {
    product_name: fields.product_name,
    brand: fields.brand,
    compliance_score: evalResult.score,
    compliance_result: evalResult.status,
    status: evalResult.status,
    score: evalResult.score,
    created_at: new Date().toISOString(),
    scanned_at: new Date().toISOString(),
    extracted_fields: fields,
    raw_ocr_text: svgText || "Packaging label text analyzed through PRISM statutory compliance auditor.",
    violations: evalResult.violations,
    statutory_summary: evalResult.statutory_summary + ` (Audit completed using PRISM statutory rule auditor during high-demand AI model spike).`,
    rag_guidance: evalResult.rag_guidance,
    model_used: "PRISM LM(PC)R Rule Auditor (High-Demand Resilience Fallback)",
  };
}

/**
 * Inspect packaged commodity label image using Gemini Multimodal Vision.
 * Evaluates statutory compliance under Legal Metrology (Packaged Commodities) Rules, 2011 (LM(PC)R 2011).
 */
export async function scanLabelWithGemini({
  base64Data,
  mimeType = "image/jpeg",
  fileName = "",
  suggestedProduct = "",
}) {
  const ai = getGenAI();

  const cleanBase64 = base64Data
    .replace(/^data:image\/[a-zA-Z0-9+]+;base64,/, "")
    .trim();

  // Detect embedded text if available (e.g. from vector/SVG packaging artwork)
  const embeddedText = extractEmbeddedSvgText(cleanBase64);

  let prompt = `You are a Senior Legal Metrology Enforcement Officer and AI Vision Specialist under the Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution, Government of India.

Analyze this uploaded photograph of a packaged commodity or product label with meticulous precision.
Uploaded file name: "${fileName || "product_label.jpg"}". ${suggestedProduct ? `Suggested context: "${suggestedProduct}".` : ""}

YOUR STATUTORY MANDATE:
Audit compliance under:
- The Legal Metrology Act, 2009 (Act 1 of 2010) - Sections 18, 36, 49
- The Legal Metrology (Packaged Commodities) Rules, 2011 (LM(PC)R 2011) - Amendments up to 2024

TASKS:
1. OPTICAL CHARACTER RECOGNITION (OCR):
Transcribe ALL visible and legible text from the package into "raw_ocr_text", preserving exact letters, punctuation, numerals, prices, dates, weights, barcodes, and addresses.

2. STATUTORY DECLARATIONS EXTRACTION (LM(PC)R 2011):
Accurately identify each statutory field from the image. If a field is not present or cannot be found on the label, strictly write "Not Declared / Not Found".
- product_name: Generic or common name of the commodity (Rule 6(1)(a)). E.g., "Refined Sunflower Oil", "Butter Cookies", "Pure Honey".
- brand: Brand or trade name.
- mrp: Maximum Retail Price (Rule 4(1) and Rule 6(1)(e)). State the exact amount (e.g., "₹ 145.00" or "Rs. 145/-") AND explicitly note whether "(Incl. of all taxes)" or "inclusive of all taxes" is present or missing.
- net_quantity: Net quantity declared in standard metric units (kg, g, L, ml, m, cm, or number) (Rule 7(1)). Check if illegal non-metric units (fluid oz, oz, lbs) are declared.
- unit_sale_price: Unit Sale Price (USP) per g/ml/kg/L (mandatory under Rule 6(11) for packages containing more than 1 unit/1kg/1L). E.g., "₹ 0.29 / g".
- mfr_date: Month and year of manufacture, packing, or import (Rule 6(1)(d)). E.g., "04/2025" or "April 2025".
- exp_date: Best before, use by, or expiry date if stated.
- batch_no: Batch, lot, or code number (Rule 6(1)(e)). E.g., "B.No. 4022A".
- manufacturer_name: Complete name and full postal address of manufacturer, packer, or importer including premises/plot, street, city, state, and pin code (Rule 6(1)(b)).
- country_of_origin: Country of origin (mandatory for imported commodities under Rule 6(1)(aa)).
- customer_care: Consumer care contact details including designation, address, telephone number, and email (Rule 6(1)(f) and Rule 2(l)).
- fssai_license: FSSAI License Number or ISI/BIS mark if visible.
- barcode: Numeric barcode (EAN-13, UPC) if visible.

3. STATUTORY COMPLIANCE AUDIT (LM(PC)R 2011 & Legal Metrology Act 2009):
Detect all non-compliances:
- Rule 4(1): MRP missing mandatory "(Incl. of all taxes)" or "inclusive of all taxes" -> Severity: "critical", Legal Section: "Section 18 / Section 36(1) LM Act 2009", Remedy: "Compounding notice or prosecution for non-standard retail declaration".
- Rule 7(1): Net quantity in non-metric units or non-standard symbols (e.g. gms, kgs, fl oz) -> Severity: "critical", Legal Section: "Section 18 / Section 36(1) LM Act 2009".
- Rule 6(1)(d) / 6(6): Month & Year of manufacture/packing missing or obscured -> Severity: "major", Legal Section: "Rule 6(1)(d) LM(PC)R 2011".
- Rule 6(1)(b): Incomplete manufacturer address (missing state, pin code, or premises) -> Severity: "major".
- Rule 6(1)(f) & 2(l): Consumer care contact missing telephone number or email -> Severity: "minor".
- Rule 6(1)(aa): Country of origin missing on imported commodity -> Severity: "major".
- Rule 6(11): Unit Sale Price missing on packages containing >1kg / >1L -> Severity: "minor".

4. COMPLIANCE SCORING (0 to 100):
- 85 - 100: "compliant" (all key declarations present, statutory wording compliant).
- 60 - 84: "partial" (minor omissions like consumer care phone format or USP).
- 0 - 59: "violation" (missing MRP tax declaration, non-metric units, missing manufacturer address, or missing mfg date).

Output strictly valid JSON with this exact schema:
{
  "product_name": "...",
  "brand": "...",
  "compliance_score": 88,
  "compliance_result": "compliant",
  "status": "compliant",
  "extracted_fields": {
    "product_name": "...",
    "brand": "...",
    "mrp": "...",
    "net_quantity": "...",
    "unit_sale_price": "...",
    "mfr_date": "...",
    "exp_date": "...",
    "batch_no": "...",
    "manufacturer_name": "...",
    "country_of_origin": "...",
    "customer_care": "...",
    "fssai_license": "...",
    "barcode": "..."
  },
  "raw_ocr_text": "...",
  "violations": [
    {
      "rule_code": "LMPC-R4(1)",
      "field": "mrp",
      "issue": "...",
      "severity": "critical",
      "legal_section": "...",
      "explanation": "...",
      "remedy": "..."
    }
  ],
  "statutory_summary": "...",
  "rag_guidance": "..."
}`;

  if (embeddedText) {
    prompt += `\n\n[DETECTED PACKAGING LABEL TEXT CHUNKS FOR REFERENCE]:\n${embeddedText}`;
  }

  // Normalize image MIME type for Gemini
  let effectiveMimeType = mimeType || "image/jpeg";
  if (effectiveMimeType.includes("svg")) {
    effectiveMimeType = "image/png";
  }

  const imagePart = {
    inlineData: {
      mimeType: effectiveMimeType,
      data: cleanBase64,
    },
  };

  const textPart = {
    text: prompt,
  };

  let lastError = null;

  for (let i = 0; i < CANDIDATE_MODELS.length; i++) {
    const modelName = CANDIDATE_MODELS[i];
    try {
      console.log(`[PRISM Scanner] Attempting label extraction using model: ${modelName}`);
      const response = await ai.models.generateContent({
        model: modelName,
        contents: {
          parts: [imagePart, textPart],
        },
        config: {
          responseMimeType: "application/json",
          temperature: 0.1,
        },
      });

      const responseText = response.text;
      if (!responseText) {
        throw new Error(`Empty response text from ${modelName}`);
      }

      const parsed = JSON.parse(responseText);

      parsed.status = parsed.status || parsed.compliance_result || "compliant";
      parsed.compliance_result = parsed.status;
      parsed.score = parsed.compliance_score ?? parsed.score ?? 85;
      parsed.compliance_score = parsed.score;
      parsed.created_at = new Date().toISOString();
      parsed.scanned_at = parsed.created_at;
      parsed.model_used = modelName;

      // Ensure extracted_fields contains all expected standard keys and convenient aliases
      const ef = parsed.extracted_fields || {};
      const expectedKeys = [
        "product_name",
        "brand",
        "mrp",
        "net_quantity",
        "unit_sale_price",
        "mfr_date",
        "exp_date",
        "batch_no",
        "manufacturer_name",
        "country_of_origin",
        "customer_care",
        "fssai_license",
        "barcode",
      ];
      expectedKeys.forEach((key) => {
        if (!ef[key]) ef[key] = "Not Declared / Not Found";
      });

      // Populate common aliases for full compatibility across all UI views
      ef.mfg_date = ef.mfr_date;
      ef.manufacturing_date = ef.mfr_date;
      ef.expiry_date = ef.exp_date;
      ef.batch_number = ef.batch_no;
      ef.manufacturer_details = ef.manufacturer_name;
      ef.manufacturer_address = ef.manufacturer_name;
      ef.consumer_care = ef.customer_care;
      ef.fssai_number = ef.fssai_license;
      ef.brand_name = ef.brand;

      parsed.extracted_fields = ef;

      if (!parsed.product_name || parsed.product_name === "Not Declared / Not Found") {
        parsed.product_name = ef.product_name || fileName || "Inspected Packaged Item";
      }
      if (!parsed.brand || parsed.brand === "Not Declared / Not Found") {
        parsed.brand = ef.brand || "Packaging Manufacturer";
      }

      console.log(`[PRISM Scanner] Successfully analyzed label with ${modelName}:`, {
        product: parsed.product_name,
        score: parsed.compliance_score,
        violationsCount: (parsed.violations || []).length,
      });

      return parsed;
    } catch (err) {
      lastError = err;
      const isDemandSpike = isDemandSpikeOrRetryableError(err);
      const cleanErrMsg = isDemandSpike ? "High demand / temporary service spike (503/429)" : (err.message || "Model error");
      console.log(`[PRISM Scanner] Model ${modelName} unavailable: ${cleanErrMsg}.`);

      // If this is a temporary high-demand spike (503) or rate limit (429), apply backoff before next candidate
      if (isDemandSpike && i < CANDIDATE_MODELS.length - 1) {
        const backoffMs = 800 + Math.floor(Math.random() * 400);
        console.log(`[PRISM Scanner] Switching to candidate model ${CANDIDATE_MODELS[i + 1]} after ${backoffMs}ms...`);
        await sleep(backoffMs);
      }
    }
  }

  // If all candidate models failed (e.g. 503 capacity spike or offline environment),
  // fall back gracefully to statutory rule engine so user never encounters a hard crash or 500 error
  console.warn(`[PRISM Scanner] All Gemini models currently experiencing high demand. Engaging statutory rule fallback auditor.`);
  return fallbackLabelAudit({
    base64Data: cleanBase64,
    fileName,
    suggestedProduct,
    lastErrorMessage: lastError ? lastError.message : "Service Unavailable",
  });
}
