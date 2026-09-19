// ─── PRISM Sample Packaging Labels for Enforcement Testing ──────────
// Generates SVG data URIs replicating authentic Indian packaged commodity labels

(function () {
  function svgToDataUrl(svgString) {
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgString.trim());
  }

  const SAMPLE_LABELS = {
    ghee_compliant: {
      id: "sample-ghee",
      title: "Amul Pure Cow Ghee 1L",
      badge: "100% Compliant",
      badgeClass: "badge-compliant",
      description: "Compliant FMCG label containing all 10 statutory declarations per LM(PC)R 2011.",
      product_name: "Amul Pure Cow Ghee 1L (Poly Pack)",
      brand: "Amul",
      getDataUrl: function () {
        return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="780" viewBox="0 0 600 780" style="background:#fffcf0;font-family:Arial, sans-serif;">
  <rect width="600" height="780" fill="#fffcf0" stroke="#d4af37" stroke-width="8"/>
  <rect x="20" y="20" width="560" height="740" fill="#ffffff" stroke="#c09825" stroke-width="2"/>
  
  <!-- Header Banner -->
  <rect x="20" y="20" width="560" height="110" fill="#c01825"/>
  <text x="300" y="65" text-anchor="middle" fill="#ffffff" font-size="34" font-weight="bold" font-family="Georgia, serif">Amul</text>
  <text x="300" y="100" text-anchor="middle" fill="#ffe082" font-size="20" font-weight="bold" letter-spacing="2">PURE COW GHEE</text>

  <!-- Commodity Generic Name -->
  <rect x="40" y="145" width="520" height="42" fill="#fff9c4" rx="6" stroke="#fbc02d" stroke-width="1"/>
  <text x="55" y="171" font-size="13" font-weight="bold" fill="#333">COMMODITY (Rule 6(1)(a)):</text>
  <text x="250" y="171" font-size="14" font-weight="bold" fill="#c01825">CLARIFIED BUTTER (COW GHEE)</text>

  <!-- Statutory Principal Display Panel Box -->
  <rect x="40" y="200" width="520" height="240" fill="#fcfcfc" stroke="#333" stroke-width="1.5" rx="4"/>
  <rect x="40" y="200" width="520" height="30" fill="#2d3748"/>
  <text x="300" y="221" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="bold">MANDATORY STATUTORY DECLARATIONS [LM(PC)R 2011]</text>

  <!-- Declarations grid -->
  <text x="55" y="255" font-size="14" font-weight="bold" fill="#111">NET QUANTITY (Rule 7):</text>
  <text x="260" y="255" font-size="15" font-weight="bold" fill="#00796b">1 L (Equivalent: 905 g)</text>

  <text x="55" y="285" font-size="14" font-weight="bold" fill="#111">MAX. RETAIL PRICE (MRP):</text>
  <text x="260" y="285" font-size="15" font-weight="bold" fill="#c01825">₹ 650.00 (Incl. of all taxes)</text>

  <text x="55" y="315" font-size="13" font-weight="bold" fill="#111">UNIT SALE PRICE (Rule 6(11)):</text>
  <text x="260" y="315" font-size="13" fill="#333">₹ 0.65 / ml</text>

  <text x="55" y="345" font-size="13" font-weight="bold" fill="#111">MFG &amp; PACKING DATE (R6(1)(d)):</text>
  <text x="310" y="345" font-size="13" font-weight="bold" fill="#111">01/2025</text>

  <text x="55" y="375" font-size="13" font-weight="bold" fill="#111">USE BY / EXPIRY DATE:</text>
  <text x="310" y="375" font-size="13" fill="#111">10/2025 (9 Months from Pkg)</text>

  <text x="55" y="405" font-size="13" font-weight="bold" fill="#111">BATCH NO. (Rule 6(1)(e)):</text>
  <text x="310" y="405" font-size="13" font-family="Courier, monospace" font-weight="bold" fill="#333">B.No. GHEE-ANAND-8894K</text>

  <!-- Manufacturer Details -->
  <rect x="40" y="455" width="520" height="95" fill="#f8fafc" stroke="#94a3b8" stroke-width="1" rx="4"/>
  <text x="55" y="475" font-size="12" font-weight="bold" fill="#0f172a">MANUFACTURED &amp; PACKED BY (Rule 6(1)(b)):</text>
  <text x="55" y="495" font-size="12" fill="#334155">Gujarat Cooperative Milk Marketing Federation Ltd. (GCMMF)</text>
  <text x="55" y="513" font-size="12" fill="#334155">Amul Dairy Road, Anand, Gujarat, India - 388001</text>
  <text x="55" y="533" font-size="12" font-weight="bold" fill="#0f172a">COUNTRY OF ORIGIN (Rule 6(1)(aa)): <tspan fill="#047857">INDIA</tspan></text>

  <!-- Consumer Care Details -->
  <rect x="40" y="560" width="520" height="95" fill="#f0fdf4" stroke="#86efac" stroke-width="1" rx="4"/>
  <text x="55" y="582" font-size="12" font-weight="bold" fill="#166534">CONSUMER CARE &amp; GRIEVANCE OFFICER (Rule 6(1)(f) &amp; Rule 2(l)):</text>
  <text x="55" y="602" font-size="12" fill="#14532d">Manager - Consumer Grievance, GCMMF Ltd., PO Box 10, Anand 388001</text>
  <text x="55" y="622" font-size="12" fill="#14532d">Toll Free: 1800-258-3333 | Email: customercare@amul.coop</text>
  <text x="55" y="642" font-size="12" font-weight="bold" fill="#166534">FSSAI Central Lic. No.: 10012021000071</text>

  <!-- Barcode Representation -->
  <rect x="40" y="668" width="520" height="75" fill="#ffffff" stroke="#e2e8f0" stroke-width="1" rx="4"/>
  <g transform="translate(180, 678)">
    <rect x="0" y="5" width="4" height="42" fill="#000"/><rect x="8" y="5" width="2" height="42" fill="#000"/>
    <rect x="14" y="5" width="6" height="42" fill="#000"/><rect x="24" y="5" width="2" height="42" fill="#000"/>
    <rect x="30" y="5" width="4" height="42" fill="#000"/><rect x="38" y="5" width="6" height="42" fill="#000"/>
    <rect x="48" y="5" width="2" height="42" fill="#000"/><rect x="54" y="5" width="4" height="42" fill="#000"/>
    <rect x="62" y="5" width="8" height="42" fill="#000"/><rect x="74" y="5" width="2" height="42" fill="#000"/>
    <rect x="80" y="5" width="4" height="42" fill="#000"/><rect x="90" y="5" width="6" height="42" fill="#000"/>
    <rect x="100" y="5" width="2" height="42" fill="#000"/><rect x="108" y="5" width="4" height="42" fill="#000"/>
    <rect x="116" y="5" width="6" height="42" fill="#000"/><rect x="126" y="5" width="2" height="42" fill="#000"/>
    <rect x="134" y="5" width="4" height="42" fill="#000"/><rect x="142" y="5" width="8" height="42" fill="#000"/>
    <rect x="154" y="5" width="2" height="42" fill="#000"/><rect x="160" y="5" width="4" height="42" fill="#000"/>
    <rect x="170" y="5" width="6" height="42" fill="#000"/><rect x="180" y="5" width="4" height="42" fill="#000"/>
    <text x="90" y="60" text-anchor="middle" font-size="12" font-family="Courier, monospace" letter-spacing="3">8901262010156</text>
  </g>
</svg>`);
      }
    },

    cookies_violation: {
      id: "sample-cookies",
      title: "Good Day Cookies 120g",
      badge: "Missing '(Incl. of all taxes)'",
      badgeClass: "badge-violation",
      description: "Violates LM(PC)R 2011 Rule 4(1): MRP printed as 'MRP Rs. 35/-' omitting statutory tax declaration.",
      product_name: "Britannia Good Day Butter Cookies 120g",
      brand: "Britannia",
      getDataUrl: function () {
        return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="780" viewBox="0 0 600 780" style="background:#fff8e1;font-family:Arial, sans-serif;">
  <rect width="600" height="780" fill="#fff8e1" stroke="#d97706" stroke-width="8"/>
  <rect x="20" y="20" width="560" height="740" fill="#ffffff" stroke="#f59e0b" stroke-width="2"/>
  
  <!-- Banner -->
  <rect x="20" y="20" width="560" height="110" fill="#b45309"/>
  <text x="300" y="65" text-anchor="middle" fill="#ffffff" font-size="32" font-weight="bold" font-family="Georgia, serif">BRITANNIA</text>
  <text x="300" y="100" text-anchor="middle" fill="#fef3c7" font-size="20" font-weight="bold">Good Day Butter Cookies</text>

  <!-- Commodity Name -->
  <rect x="40" y="145" width="520" height="42" fill="#fef2f2" rx="6" stroke="#fca5a5" stroke-width="1"/>
  <text x="55" y="171" font-size="13" font-weight="bold" fill="#111">GENERIC COMMODITY:</text>
  <text x="230" y="171" font-size="14" font-weight="bold" fill="#991b1b">BISCUITS / BAKED CONFECTIONERY</text>

  <!-- Panel with statutory violation -->
  <rect x="40" y="200" width="520" height="240" fill="#fff5f5" stroke="#dc2626" stroke-width="2" rx="4"/>
  <rect x="40" y="200" width="520" height="30" fill="#dc2626"/>
  <text x="300" y="221" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="bold">PACKAGING STATUTORY DETAILS [DEFECTIVE DECLARATIONS]</text>

  <text x="55" y="255" font-size="14" font-weight="bold" fill="#111">NET QUANTITY:</text>
  <text x="240" y="255" font-size="15" font-weight="bold" fill="#111">120 g</text>

  <!-- VIOLATION HERE: NO INCL OF ALL TAXES -->
  <rect x="50" y="268" width="500" height="36" fill="#fee2e2" stroke="#ef4444" stroke-dasharray="4,4"/>
  <text x="55" y="291" font-size="14" font-weight="bold" fill="#b91c1c">MRP (VIOLATION R4(1)):</text>
  <text x="240" y="291" font-size="16" font-weight="bold" fill="#dc2626">Rs. 35.00 only [TAXES NOT STATED]</text>

  <text x="55" y="325" font-size="13" font-weight="bold" fill="#111">UNIT SALE PRICE:</text>
  <text x="240" y="325" font-size="13" fill="#333">₹ 0.29 / g</text>

  <text x="55" y="355" font-size="13" font-weight="bold" fill="#111">MFG DATE:</text>
  <text x="240" y="355" font-size="13" fill="#111">02/2025</text>

  <text x="55" y="385" font-size="13" font-weight="bold" fill="#111">BATCH NO:</text>
  <text x="240" y="385" font-size="13" font-family="Courier, monospace" fill="#111">B.No. BT-2911C</text>

  <text x="55" y="415" font-size="13" font-weight="bold" fill="#111">BEST BEFORE:</text>
  <text x="240" y="415" font-size="13" fill="#111">6 months from manufacture</text>

  <!-- Manufacturer details -->
  <rect x="40" y="455" width="520" height="90" fill="#f8fafc" stroke="#94a3b8" stroke-width="1" rx="4"/>
  <text x="55" y="475" font-size="12" font-weight="bold" fill="#0f172a">MANUFACTURED BY:</text>
  <text x="55" y="495" font-size="12" fill="#334155">Britannia Industries Limited, 5/1A Hungerford Street, Kolkata - 700017</text>
  <text x="55" y="520" font-size="12" font-weight="bold" fill="#0f172a">Country of Origin: INDIA</text>

  <!-- Missing phone grievance violation -->
  <rect x="40" y="555" width="520" height="90" fill="#fff7ed" stroke="#f97316" stroke-width="1" rx="4"/>
  <text x="55" y="575" font-size="12" font-weight="bold" fill="#c2410c">CONSUMER CARE (INCOMPLETE R6(1)(f)):</text>
  <text x="55" y="597" font-size="12" fill="#9a3412">Consumer Services Executive, PO Box 6000, Kolkata 700017</text>
  <text x="55" y="618" font-size="12" fill="#dc2626">[VIOLATION: No Consumer Care Telephone or Toll Free Number declared]</text>

  <!-- Barcode -->
  <rect x="40" y="660" width="520" height="85" fill="#ffffff" stroke="#e2e8f0" rx="4"/>
  <g transform="translate(180, 675)">
    <rect x="0" y="5" width="4" height="42" fill="#000"/><rect x="10" y="5" width="6" height="42" fill="#000"/>
    <rect x="22" y="5" width="4" height="42" fill="#000"/><rect x="34" y="5" width="8" height="42" fill="#000"/>
    <rect x="48" y="5" width="4" height="42" fill="#000"/><rect x="60" y="5" width="6" height="42" fill="#000"/>
    <rect x="74" y="5" width="4" height="42" fill="#000"/><rect x="88" y="5" width="6" height="42" fill="#000"/>
    <rect x="100" y="5" width="4" height="42" fill="#000"/><rect x="112" y="5" width="8" height="42" fill="#000"/>
    <rect x="128" y="5" width="4" height="42" fill="#000"/><rect x="140" y="5" width="6" height="42" fill="#000"/>
    <text x="80" y="60" text-anchor="middle" font-size="12" font-family="Courier, monospace">8901063132014</text>
  </g>
</svg>`);
      }
    },

    olive_oil_violation: {
      id: "sample-olive-oil",
      title: "Imported Olive Oil",
      badge: "Non-Metric Units (fl oz)",
      badgeClass: "badge-violation",
      description: "Violates LM(PC)R Rule 7(1) via illegal non-metric declaration '16.9 FL. OZ.' and Rule 6(1)(aa) missing Country of Origin.",
      product_name: "Bella Terra Extra Virgin Olive Oil",
      brand: "Bella Terra",
      getDataUrl: function () {
        return svgToDataUrl(`
<svg xmlns="http://www.w3.org/2000/svg" width="600" height="780" viewBox="0 0 600 780" style="background:#f0fdf4;font-family:Arial, sans-serif;">
  <rect width="600" height="780" fill="#f0fdf4" stroke="#15803d" stroke-width="8"/>
  <rect x="20" y="20" width="560" height="740" fill="#ffffff" stroke="#16a34a" stroke-width="2"/>
  
  <rect x="20" y="20" width="560" height="110" fill="#14532d"/>
  <text x="300" y="65" text-anchor="middle" fill="#ffffff" font-size="30" font-weight="bold" font-family="Georgia, serif">BELLA TERRA</text>
  <text x="300" y="100" text-anchor="middle" fill="#bbf7d0" font-size="18" font-weight="bold">EXTRA VIRGIN OLIVE OIL</text>

  <rect x="40" y="145" width="520" height="42" fill="#fef2f2" rx="6" stroke="#fca5a5" stroke-width="1"/>
  <text x="55" y="171" font-size="13" font-weight="bold" fill="#111">NAME OF COMMODITY:</text>
  <text x="230" y="171" font-size="14" font-weight="bold" fill="#15803d">EDIBLE EXTRA VIRGIN OLIVE OIL</text>

  <rect x="40" y="200" width="520" height="240" fill="#fff1f2" stroke="#e11d48" stroke-width="2" rx="4"/>
  <rect x="40" y="200" width="520" height="30" fill="#be123c"/>
  <text x="300" y="221" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="bold">STATUTORY AUDIT PANEL [PROHIBITED NON-METRIC UNITS]</text>

  <!-- CRITICAL VIOLATION: FLUID OUNCE -->
  <rect x="50" y="240" width="500" height="40" fill="#ffe4e6" stroke="#f43f5e"/>
  <text x="55" y="265" font-size="14" font-weight="bold" fill="#9f1239">NET QUANTITY (VIOLATION R7(1)):</text>
  <text x="320" y="265" font-size="16" font-weight="bold" fill="#be123c">16.9 FL. OZ. [NON-METRIC]</text>

  <text x="55" y="305" font-size="14" font-weight="bold" fill="#111">MAX RETAIL PRICE (MRP):</text>
  <text x="320" y="305" font-size="15" font-weight="bold" fill="#be123c">₹ 899.00 (Incl. of all taxes)</text>

  <text x="55" y="335" font-size="13" font-weight="bold" fill="#111">DATE OF PACKING / IMPORT:</text>
  <text x="320" y="335" font-size="13" fill="#111">11/2024</text>

  <text x="55" y="365" font-size="13" font-weight="bold" fill="#111">EXPIRY DATE:</text>
  <text x="320" y="365" font-size="13" fill="#111">11/2026</text>

  <text x="55" y="395" font-size="13" font-weight="bold" fill="#111">BATCH IDENTIFICATION:</text>
  <text x="320" y="395" font-size="13" font-family="Courier, monospace">LOT # SP-9022-X</text>

  <!-- Importer and Missing Country of Origin -->
  <rect x="40" y="455" width="520" height="95" fill="#fff7ed" stroke="#fb923c" stroke-width="1" rx="4"/>
  <text x="55" y="475" font-size="12" font-weight="bold" fill="#9a3412">IMPORTED &amp; MARKETED IN INDIA BY:</text>
  <text x="55" y="495" font-size="12" fill="#7c2d12">Continental Gourmet Importers Pvt. Ltd., Nariman Point, Mumbai 400021</text>
  <text x="55" y="520" font-size="12" font-weight="bold" fill="#dc2626">COUNTRY OF ORIGIN (VIOLATION R6(1)(aa)): [NOT DECLARED ON PACK]</text>

  <!-- Consumer Care -->
  <rect x="40" y="560" width="520" height="85" fill="#f8fafc" stroke="#cbd5e1" rx="4"/>
  <text x="55" y="580" font-size="12" font-weight="bold" fill="#334155">CONSUMER CARE CONTACT:</text>
  <text x="55" y="602" font-size="12" fill="#475569">Manager - Customer Feedback, Nariman Point, Mumbai 400021</text>
  <text x="55" y="622" font-size="12" fill="#475569">Email: help@continentalltd.in | Tel: 022-66991122</text>

  <!-- Barcode -->
  <rect x="40" y="655" width="520" height="90" fill="#ffffff" stroke="#e2e8f0" rx="4"/>
  <g transform="translate(180, 670)">
    <rect x="0" y="5" width="4" height="42" fill="#000"/><rect x="8" y="5" width="4" height="42" fill="#000"/>
    <rect x="18" y="5" width="8" height="42" fill="#000"/><rect x="32" y="5" width="4" height="42" fill="#000"/>
    <rect x="44" y="5" width="6" height="42" fill="#000"/><rect x="58" y="5" width="4" height="42" fill="#000"/>
    <rect x="70" y="5" width="8" height="42" fill="#000"/><rect x="84" y="5" width="4" height="42" fill="#000"/>
    <rect x="96" y="5" width="6" height="42" fill="#000"/><rect x="110" y="5" width="4" height="42" fill="#000"/>
    <rect x="124" y="5" width="8" height="42" fill="#000"/><rect x="140" y="5" width="4" height="42" fill="#000"/>
    <text x="80" y="60" text-anchor="middle" font-size="12" font-family="Courier, monospace">0841029100412</text>
  </g>
</svg>`);
      }
    }
  };

  function svgToPngBlob(svgDataUrl, width = 600, height = 780) {
    return new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        try {
          const canvas = document.createElement("canvas");
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext("2d");
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(0, 0, width, height);
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob((blob) => {
            if (blob) {
              resolve(blob);
            } else {
              fetch(svgDataUrl).then(r => r.blob()).then(resolve).catch(() => resolve(null));
            }
          }, "image/png");
        } catch (e) {
          fetch(svgDataUrl).then(r => r.blob()).then(resolve).catch(() => resolve(null));
        }
      };
      img.onerror = () => {
        fetch(svgDataUrl).then(r => r.blob()).then(resolve).catch(() => resolve(null));
      };
      img.src = svgDataUrl;
    });
  }

  SAMPLE_LABELS.getPngBlob = async function (key) {
    const item = SAMPLE_LABELS[key];
    if (!item) return null;
    const url = item.getDataUrl();
    return await svgToPngBlob(url);
  };

  SAMPLE_LABELS.rasterizeSvgToPngBlob = svgToPngBlob;

  window.SAMPLE_LABELS = SAMPLE_LABELS;
})();
