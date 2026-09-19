PRISM — Legal Metrology Compliance System

AI-powered compliance inspection and pre-compliance platform for packaged commodities under India's Legal Metrology framework.

PRISM is a full-stack React + TypeScript application designed to demonstrate how packaged-commodity compliance checks can be digitized for inspectors, supervisors, administrators, manufacturers, and consumers.

The platform combines a role-based portal system, deterministic Legal Metrology rule validation, AI-assisted package/label analysis through Gemini, inspection history, consumer grievance management, analytics, and PDF report generation.

✨ Key Features

🏛️ Role-Based Portals

PRISM supports five user roles:

Inspector

Scan packaged-commodity labels using image upload or camera

Run compliance inspections

Review detected declarations and violations

View inspection history

Generate compliance/inspection PDF reports

Issue formal notices from inspection results

Supervisor

Monitor inspection activity

Review enforcement-related data

Track regional/system metrics

Administrator

Manage system users

Activate/suspend users

View and update Legal Metrology rule settings

Review analytics and operational metrics

Manufacturer

Upload packaging artwork/label designs

Run pre-print compliance checks

Identify missing or potentially non-compliant declarations

Review compliance score and recommendations

Generate inspection/compliance reports

Complete manufacturer onboarding

Consumer

Scan a packaged product

Review detected compliance issues

Submit a consumer grievance

Track grievance/ticket status

🤖 AI-Assisted Compliance Analysis

The application can use the Google Gemini API to analyze uploaded package/label images.

The server-side scan flow can extract or assess information such as:

Manufacturer / packer / importer details

Commodity name

Net quantity

Measurement unit

MRP

Tax-inclusion wording

Date of packing/manufacture

Consumer-care information

Country of origin

Label/font-related information

Other potentially relevant declarations

The extracted information is then passed through PRISM's deterministic rule engine.

Important: AI analysis is an assistive feature. The application's rule engine performs the compliance evaluation using configured rules; real-world legal/enforcement decisions should be independently verified against the current applicable legislation, rules, notifications, and official guidance.

⚖️ Deterministic Legal Metrology Rule Engine

PRISM includes a dedicated rule engine in:

src/services/ruleEngine.ts

It currently contains configurable checks related to areas including:

Rule 6 mandatory declarations

Net quantity declarations

Standard measurement units

MRP declaration

"Inclusive of all taxes" wording

Font-size requirements based on Principal Display Panel (PDP) area

Consumer-care declarations

Country-of-origin checks

Other configured compliance conditions

The rule engine produces:

Compliance Status
Compliance Score
Violations
Legal Citations

Example result

Score: 75 / 100
Status: NON_COMPLIANT

Violations:
- Missing Manufacturer / Packer Name & Address
- Missing MRP
- Non-standard measurement unit

Legal Citations:
- Rule 6(1)(a)
- Rule 6(1)(e)
- Rule 11

Rule configuration is represented by:

MetrologyRuleSettings
RuleConfigScheduleItem

in:

src/types.ts

📄 PDF Report Generation

PRISM can generate formal inspection/compliance PDFs using jsPDF.

Generated reports can contain:

Reference number

Inspection date/time

Inspector details

Compliance score

Product information

Store/establishment information

Mandatory declaration checks

Detected violations

Legal citations

Suggested corrective actions

Statutory statements

Signature sections

The PDF generation logic is located at:

src/services/pdfGenerator.ts

👥 User & Grievance Management

The backend provides APIs for:

Authentication

Manufacturer onboarding

User profiles

User administration

Inspection records

Consumer grievances

Grievance status updates

Analytics

Rule configuration

Real-time metrics

Consumer grievance statuses include:

SUBMITTED
ASSIGNED
VERIFIED
NOTICE_ISSUED
DISMISSED

🌐 Internationalization

PRISM includes a translation service:

src/services/i18n.ts

The interface is designed to support multiple languages, with language preference persisted in browser local storage.

The application also includes IST-aware greeting/time functionality through:

src/services/istTime.ts

🎨 UI / UX

The frontend uses a modern dashboard-oriented interface with:

Responsive layouts

Light and dark themes

Role-specific dashboards

Glass/gradient visual treatments

Status badges

Compliance score cards

Inspection history

Modals and dialogs

Camera access

Image upload

Interactive analytics

Lucide icons

Motion-based UI interactions

Theme preference is stored locally using:

lmpc_theme

Language preference is stored using:

lmpc_lang

🧱 Tech Stack

Frontend

React 19

TypeScript

Vite

Tailwind CSS

Lucide React

Motion

Backend

Node.js

Express

TypeScript

tsx

esbuild

AI

Google Gemini API

@google/genai

Document Generation

jsPDF

Development

Bun lockfile

Vite development server

TypeScript compiler

📁 Project Structure

PRISM-main/
│
├── .env.example
├── .gitignore
├── README.md
├── bun.lock
├── index.html
├── metadata.json
├── package.json
├── server.ts
├── tsconfig.json
├── vite.config.ts
│
└── src/
    ├── App.tsx
    ├── index.css
    ├── main.tsx
    ├── types.ts
    │
    ├── components/
    │   ├── AdminDashboard.tsx
    │   ├── AuthModal.tsx
    │   ├── ConsumerPortal.tsx
    │   ├── Header.tsx
    │   ├── InspectorDashboard.tsx
    │   ├── InspectorDashboard.tsx
    │   ├── LegalNoticeModal.tsx
    │   ├── MainHomePage.tsx
    │   ├── ManufacturerOnboardingModal.tsx
    │   ├── ManufacturerPortal.tsx
    │   ├── SupervisorDashboard.tsx
    │   └── UserProfileModal.tsx
    │
    └── services/
        ├── i18n.ts
        ├── istTime.ts
        ├── pdfGenerator.ts
        ├── ruleEngine.ts
        └── sampleData.ts

The exact component list can evolve as the project is developed.

🔄 Application Flow

                    ┌──────────────────────┐
                    │     PRISM Home       │
                    │   National Landing   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Authentication    │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
        Government         Industry          Consumer
         Portals            Portal            Portal
             │                 │                 │
       ┌─────┼─────┐          │                 │
       │     │     │          ▼                 ▼
       ▼     ▼     ▼    Pre-Compliance     Product Scan
    Admin  Supv  Insp       Analysis            │
       │     │     │          │                 ▼
       │     │     │          └──────────► Grievance
       │     │     │
       └─────┴─────┴──────────────┐
                                  ▼
                         Compliance Engine
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                  Score       Violations     Citations
                    │             │             │
                    └─────────────┼─────────────┘
                                  ▼
                           PDF / Notice

🔌 API Endpoints

The Express backend currently exposes routes including:

Method

Endpoint

Purpose

GET

/api/health

Health/status check

POST

/api/auth/login

Role-based authentication

POST

/api/user/onboard-manufacturer

Manufacturer onboarding

GET

/api/user/profile/:id

Get user profile

PATCH

/api/user/profile/:id

Update user profile

GET

/api/metrics/realtime

Real-time dashboard metrics

POST

/api/scan

AI-assisted package scan + compliance evaluation

POST

/api/manufacturer/pre-check

Manufacturer pre-compliance workflow

POST

/api/consumer/grievance

Submit consumer grievance

GET

/api/inspections

List inspections

GET

/api/inspections/:id

Get inspection details

GET

/api/grievances

List grievances

PATCH

/api/grievances/:id

Update grievance

GET

/api/analytics

Analytics data

GET

/api/admin/users

List administrative users

POST

/api/admin/users

Create a user

PATCH

/api/admin/users/:id/status

Activate/suspend a user

GET

/api/admin/rules

Get rule configuration

PUT

/api/admin/rules

Update rule configuration

🚀 Getting Started

1. Prerequisites

Install:

Node.js 18+

npm, pnpm, or Bun

A Google Gemini API key for AI-powered image analysis

Check your Node.js installation:

node --version

Check npm:

npm --version

2. Extract the Project

cd PRISM-main

3. Install Dependencies

Using npm:

npm install

Or using Bun:

bun install

4. Configure Environment Variables

Create a .env file in the project root.

You can start from:

.env.example

Example:

GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
APP_URL="http://localhost:3000"

Gemini API Key

The application reads:

GEMINI_API_KEY

from the server environment.

Keep your API key private and never commit the .env file to GitHub.

▶️ Run the Development Server

The project uses:

"dev": "tsx server.ts"

Run:

npm run dev

or:

bun run dev

The Express server starts on:

http://localhost:3000

The Vite middleware serves the React application.

🏗️ Production Build

Build the frontend and bundled server:

npm run build

Then start the production server:

npm start

The build process creates the server bundle under:

dist/server.cjs

🧪 Type Checking

Run:

npm run lint

This executes:

tsc --noEmit

and helps detect TypeScript errors without creating compiled output.

🔐 Authentication & Identity Management

PRISM implements dual-layer authentication:
- Government staff roles authenticate via Department user ID and password.
- Citizen and Manufacturer roles authenticate via Phone OTP verification.
- In production with Supabase configured, full Supabase Auth + JWT token validation is enforced.

Audit logging

Secret management

CSRF protection where applicable

🗄️ Data Storage

The current backend uses in-memory arrays seeded from:

src/services/sampleData.ts

Examples include:

INITIAL_USERS
INITIAL_INSPECTIONS
INITIAL_GRIEVANCES

This means data can be lost when the server restarts.

Recommended production architecture

Replace the in-memory stores with a real database such as:

PostgreSQL
        │
        ▼
User Management
Inspection Records
Grievances
Rule Configuration
Audit Logs

A production implementation could also use:

Supabase

PostgreSQL + Prisma/Drizzle

Managed cloud database

Object storage for evidence images

Redis for caching/queues

📷 Camera & Image Upload

Inspectors and consumers can upload package images.

The inspector portal can also request camera access using the browser:

navigator.mediaDevices.getUserMedia()

Camera functionality generally requires a secure browser context such as:

HTTPS

or:

localhost

Users must grant browser camera permission.

🧠 Compliance Scoring

PRISM starts compliance evaluation with:

100 points

Configured violations deduct points according to their severity/rule.

The final result contains:

{
  overallStatus,
  score,
  violations,
  legalCitations
}

Possible overall statuses:

COMPLIANT
WARNING
NON_COMPLIANT

The scoring system is a software implementation for this project and should not be treated as an official statutory penalty calculation.

📊 Core Data Models

Important TypeScript interfaces are defined in:

src/types.ts

Key models include:

User

User

Represents:

Inspectors

Supervisors

Administrators

Manufacturers

Consumers

InspectionRecord

Stores:

Product information

Store information

Inspector information

Image/evidence

Compliance score

Violations

Declarations

Legal citations

Notice information

ConsumerGrievance

Stores:

Consumer information

Product information

Store information

Complaint description

Evidence

Detected violations

Ticket status

MetrologyRuleSettings

Stores configurable compliance settings such as:

Font-size schedules

Allowed units

MRP phrases

Thresholds

Consumer-care checks

Country-of-origin settings

Penalty configuration

🛠️ Development Roadmap

Phase 1 — Prototype

Role-based dashboards

Package image upload

Camera interface

Gemini integration

Deterministic compliance engine

Compliance scoring

Violation detection

PDF generation

Consumer grievance flow

Admin user management

Rule configuration

Dark/light theme

Multi-language foundation

Phase 2 — Production Backend

PostgreSQL/Supabase database

Secure authentication

Real OTP service

Role-based authorization middleware

Persistent evidence storage

Audit logs

Database migrations

API validation

Rate limiting

Centralized error handling

Phase 3 — Advanced AI

Improved OCR pipeline

Structured declaration extraction

Better font-size estimation

Barcode/GTIN verification

Multi-image inspection

Confidence scores

Human-review workflow

AI explanation for detected issues

Phase 4 — Government/Enterprise Deployment

Production identity integration

State/region jurisdiction management

Official rule-update workflow

Secure audit trails

Evidence retention policies

Monitoring and observability

Automated notifications

Deployment security review

🔒 Security Considerations

Before production deployment, review at minimum:

Remove all demo credentials.

Never expose GEMINI_API_KEY to the browser.

Add authentication middleware to protected API routes.

Validate and sanitize all incoming request data.

Add rate limiting to authentication and AI endpoints.

Restrict uploaded file types and file sizes.

Store evidence files in secure object storage.

Add audit logging for inspections and administrative actions.

Protect sensitive consumer/manufacturer information.

Use HTTPS in production.

Implement proper session/token expiration.

Keep dependencies updated.

Review legal-rule configuration against current official sources before operational use.

⚠️ Legal & Compliance Disclaimer

PRISM is a software prototype / demonstration system intended to show how AI-assisted compliance workflows can be implemented.

The application references Legal Metrology concepts and rules for software evaluation. It should not be treated as an official government system, legal opinion, statutory determination, or substitute for verification by authorized officials or qualified legal/regulatory professionals.

Legal requirements, notifications, amendments, exemptions, penalties, and enforcement procedures can change. Any production deployment should use an authoritative, version-controlled legal source and an appropriate review process.

🤝 Contributing

Contributions can follow this workflow:

git clone <repository-url>
cd PRISM-main
npm install
npm run dev

Create a feature branch:

git checkout -b feature/your-feature

Make your changes, test them, and then open a pull request.

Suggested contribution areas:

UI/UX improvements

Rule-engine improvements

Accessibility

Test coverage

Database integration

Security hardening

AI extraction accuracy

Performance optimization

📜 License

The application source includes an Apache-2.0 SPDX license header in the frontend entry point.

If this repository is distributed as a complete project, include the appropriate Apache License 2.0 text and verify that all third-party dependencies and assets comply with their respective licenses.

👨‍💻 Project Overview

Project: PRISM
Full Name: Legal Metrology Compliance System
Domain: AI + Legal Metrology + Compliance + Government/Regulatory Technology
Primary Use Cases: Field Inspection, Manufacturer Pre-Compliance, Consumer Grievances, Administrative Monitoring

Main Technologies

React
TypeScript
Vite
Express
Node.js
Tailwind CSS
Google Gemini
jsPDF
Lucide React
Motion

⭐ PRISM in One Sentence

PRISM turns packaged-commodity compliance inspection into a digital workflow that combines AI-assisted label analysis, deterministic rule validation, role-based operations, consumer reporting, and automated documentation.
