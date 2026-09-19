# PRISM (Packaged Rules Inspection & Scanning Mechanism)

**Vanilla HTML + CSS + JS** frontend · **FastAPI + Python** backend · **Supabase** auth/storage · **PostgreSQL** database.

> No React, no TypeScript, no Tailwind. Plain HTML multi-page app served by Vite dev server.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5 + CSS3 + Vanilla JS (no framework) |
| Backend | FastAPI + Python 3.11, deployed on Render Web Service |
| Database | PostgreSQL, initialized via `backend/db/init_db.py` |
| Auth | Supabase Auth (email+password for staff; Phone OTP for manufacturer/consumer) |
| Storage | Supabase Bucket Storage (label images, reports) |
| Image Processing | OpenCV + Pillow + pytesseract (OCR) |
| Rule Engine | Python rule engine + keyword-RAG (LM(PC)R 2011) |
| Frontend Deploy | Vercel (static, `frontend/` directory) |
| Backend Deploy | Render Web Service |

## Development Server

A Vite development server is **already running** on `$PORT` (default 8443). It serves the `frontend/` directory.

- Preview URL: accessible through the Figma Make preview panel
- Hot reload: changes to `frontend/` files reload immediately

## Project Structure

```
/
├── frontend/                  ← Vite root; all HTML/CSS/JS lives here
│   ├── index.html             ← Login page (role selection + auth)
│   ├── vercel.json            ← Vercel deployment + rewrites config
│   ├── css/
│   │   └── styles.css         ← All styles (CSS custom properties, no Tailwind)
│   ├── js/
│   │   ├── config.js          ← CONFIG object, LANGUAGES array, t() i18n helper
│   │   ├── auth.js            ← Supabase Auth: loginWithPassword, requestOTP, verifyOTP, requireAuth, logout
│   │   ├── api.js             ← FastAPI client (API object) + mock data for DEMO_MODE
│   │   └── utils.js           ← initTheme, toggleTheme, renderGlobalBar, showToast, fmtDate, scoreRingHTML, …
│   └── pages/
│       ├── inspector.html     ← Inspector dashboard (scan, history, violations, reports)
│       ├── supervisor.html    ← Supervisor dashboard (team overview, approvals, analytics)
│       ├── admin.html         ← Admin dashboard (user mgmt, system reports, audit logs)
│       ├── manufacturer.html  ← Manufacturer dashboard (scan label, my products, reports)
│       └── consumer.html      ← Consumer dashboard (scan, history, help/FAQ)
│
├── backend/                   ← FastAPI Python backend
│   ├── main.py                ← FastAPI app, CORS, routers, /health endpoint
│   ├── requirements.txt       ← Python dependencies (pinned)
│   ├── render.yaml            ← Render.com deployment config
│   ├── .env.example           ← Required environment variables
│   ├── db/
│   │   ├── connection.py      ← psycopg2 connection factory
│   │   └── init_db.py         ← Idempotent schema creation + seed data
│   ├── models/
│   │   └── schemas.py         ← Pydantic v2 request/response models
│   ├── routers/
│   │   ├── auth_router.py     ← /api/auth/* — JWT verify, OTP, /me
│   │   ├── scan_router.py     ← /api/scan/* — image upload, OCR, rules, history
│   │   ├── reports_router.py  ← /api/reports/* — list, generate (PDF/Excel), download
│   │   ├── users_router.py    ← /api/users/* — CRUD, admin-gated
│   │   └── products_router.py ← /api/products/*, /api/dashboard/* — stats, violations
│   └── services/
│       ├── ocr_service.py     ← OpenCV preprocessing → Tesseract → field regex parser
│       ├── rule_engine.py     ← LM(PC)R 2011 compliance checker, 9 rules, scoring
│       ├── rag_service.py     ← Keyword-based RAG over 14 legal knowledge entries
│       ├── report_service.py  ← ReportLab PDF + openpyxl Excel report generation
│       └── storage_service.py ← Supabase Storage upload/delete with demo fallback
│
├── package.json               ← Only Vite as devDependency (no React/TS)
├── vite.config.js             ← root: "frontend", MPA entry points
└── .mise.toml                 ← Node.js + pnpm toolchain versions
```

## Styling

All styles are in `frontend/css/styles.css` using **CSS custom properties** (no Tailwind, no preprocessor).

**Fonts** (Google Fonts CDN, imported at top of styles.css):
- `--font-display: 'Fraunces'` — headings
- `--font-sans: 'Inter'` — body text
- `--font-mono: 'JetBrains Mono'` — code, IDs

**Theme tokens** (light/dark via `data-theme` on `<html>`):
- `--bg-page`, `--bg-card`, `--text-base`, `--text-muted`, `--border`
- `--parchment`, `--navy-900: #1a2f5a`, `--amber-600: #d97706`

## JS Architecture

Each HTML page loads these scripts in order:
1. `config.js` — `CONFIG`, `LANGUAGES`, `STRINGS`, `t(key, lang)`
2. `auth.js` — Supabase session management, `requireAuth(role)`, `logout()`
3. `api.js` — `API` object with mock fallback when `CONFIG.DEMO_MODE = true`
4. `utils.js` — `initTheme()`, `renderGlobalBar()`, toast, date helpers

**Dashboard page init pattern:**
```js
initTheme();
renderGlobalBar();
const session = requireAuth('rolename');  // redirects to / if not authenticated
```

## User Roles & Auth

| Role | Auth Method | User ID Format |
|------|------------|---------------|
| Admin | Email + Password | `admin` |
| Inspector | Email + Password | `rajesh.agarwal` |
| Supervisor | Email + Password | `meera.krishnan` |
| Manufacturer | Phone OTP | `MFR91_YYYY_XXXX` |
| Consumer | Phone OTP | `CTZN91_YYYY_XXXX` |

## Authentication Configuration

Authentication is managed via official departmental credentials and verified Phone OTP.

## Code Quality

- Use double quotes for strings with apostrophes: `"We're here"` not `'We\'re here'`
- No TypeScript — plain `.js` files only
- No JSX — plain DOM manipulation
- Do not add `<script type="module">` in pages (CDN scripts don't support ES modules in this setup)
