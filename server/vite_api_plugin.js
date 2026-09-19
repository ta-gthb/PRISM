import { scanLabelWithGemini } from "./gemini_scanner.js";
import { evaluateFieldsCompliance } from "./statutory_rules.js";

export { evaluateFieldsCompliance };

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
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(json),
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  });
  res.end(json);
}

function addApiRoutes(middlewares) {
  middlewares.use(async (req, res, next) => {
    const url = req.url || "";

    if (req.method === "OPTIONS") {
      res.writeHead(200, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      });
      return res.end();
    }

    // ── POST /api/scan/image ───────────────────────────────────────────
    if (url.startsWith("/api/scan/image") && req.method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const contentType = req.headers["content-type"] || "";

        let base64Data = "";
        let mimeType = "image/jpeg";
        let fileName = "uploaded_label.jpg";
        let suggestedProduct = "";

        if (contentType.includes("application/json")) {
          const body = JSON.parse(rawBuffer.toString("utf-8"));
          base64Data = body.image_base64 || body.image || body.file || "";
          mimeType = body.mime_type || "image/jpeg";
          fileName = body.file_name || fileName;
          suggestedProduct = body.product_name || "";
        } else if (contentType.includes("multipart/form-data")) {
          // Parse multipart form
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
            error: "Missing image data in request. Provide image_base64 in JSON or file in multipart form.",
          });
        }

        console.log(`[PRISM API] Received image scan request: "${fileName}" (${mimeType}, base64 len: ${base64Data.length})`);

        const scanResult = await scanLabelWithGemini({
          base64Data,
          mimeType,
          fileName,
          suggestedProduct,
        });

        return sendJson(res, 200, scanResult);
      } catch (err) {
        console.error("[PRISM API] Scan error:", err);
        return sendJson(res, 500, {
          error: "Failed to scan label with AI engine: " + err.message,
          detail: err.stack,
        });
      }
    }

    // ── POST /api/scan/reevaluate ──────────────────────────────────────
    if (url.startsWith("/api/scan/reevaluate") && req.method === "POST") {
      try {
        const rawBuffer = await readBody(req);
        const body = JSON.parse(rawBuffer.toString("utf-8"));
        const evaluation = evaluateFieldsCompliance(body.extracted_fields || {});
        return sendJson(res, 200, evaluation);
      } catch (err) {
        return sendJson(res, 400, { error: err.message });
      }
    }

    // ── GET /api/scan/health ───────────────────────────────────────────
    if (url.startsWith("/api/scan/health")) {
      return sendJson(res, 200, {
        status: "healthy",
        engine: "Gemini 3.8 Flash Vision + LM(PC)R 2011 Statutory Rule Auditor",
        timestamp: new Date().toISOString(),
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
