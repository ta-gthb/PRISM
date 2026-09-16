"""
Database initialisation script.

Run directly:  python db/init_db.py
Or called as part of the Render build command.

Creates all tables (idempotent — uses CREATE TABLE IF NOT EXISTS) and seeds
seed users so the system is usable immediately after first deploy.
"""

import os
import uuid
from dotenv import load_dotenv

load_dotenv()

from db.connection import get_db_connection  # noqa: E402 (after load_dotenv)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

CREATE_EXTENSIONS = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
"""

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           TEXT        UNIQUE,
    supabase_user_id  TEXT        UNIQUE,
    role              TEXT        NOT NULL DEFAULT 'inspector'
                                  CHECK (role IN ('admin','inspector','supervisor','manufacturer','consumer')),
    name              TEXT        NOT NULL,
    email             TEXT        UNIQUE NOT NULL,
    mobile            TEXT,
    organization      TEXT,
    state             TEXT,
    designation       TEXT,
    gstin             TEXT,
    is_active         BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_PRODUCTS_TABLE = """
CREATE TABLE IF NOT EXISTS products (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    barcode           TEXT        UNIQUE,
    name              TEXT        NOT NULL,
    brand             TEXT,
    manufacturer_id   UUID        REFERENCES users(id) ON DELETE SET NULL,
    net_quantity      TEXT,
    mrp               NUMERIC(12,2),
    mfr_date          TEXT,
    exp_date          TEXT,
    compliance_status TEXT        NOT NULL DEFAULT 'unknown'
                                  CHECK (compliance_status IN
                                         ('compliant','partial','violation','unknown')),
    scan_count        INTEGER     NOT NULL DEFAULT 0,
    last_scanned_at   TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_SCANS_TABLE = """
CREATE TABLE IF NOT EXISTS scans (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_name       TEXT,
    brand              TEXT,
    image_url          TEXT,
    extracted_fields   JSONB       NOT NULL DEFAULT '{}',
    compliance_result  TEXT        NOT NULL DEFAULT 'violation'
                                   CHECK (compliance_result IN
                                          ('compliant','partial','violation')),
    compliance_score   INTEGER     NOT NULL DEFAULT 0
                                   CHECK (compliance_score BETWEEN 0 AND 100),
    violations         JSONB       NOT NULL DEFAULT '[]',
    rag_guidance       TEXT,
    consumer_reported  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_VIOLATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS violations (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id           UUID        NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    rule_code         TEXT        NOT NULL,
    field_name        TEXT        NOT NULL,
    issue_description TEXT        NOT NULL,
    severity          TEXT        NOT NULL DEFAULT 'minor'
                                  CHECK (severity IN ('critical','major','minor')),
    legal_explanation TEXT,
    rag_context       TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS reports (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT        NOT NULL,
    report_type TEXT        NOT NULL DEFAULT 'summary'
                            CHECK (report_type IN
                                   ('summary','detailed','violation','product','audit')),
    format      TEXT        NOT NULL DEFAULT 'pdf'
                            CHECK (format IN ('pdf','excel','csv')),
    file_url    TEXT,
    filters     JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_AUDIT_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT        NOT NULL,
    resource   TEXT        NOT NULL,
    details    JSONB       NOT NULL DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_scans_user_id        ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_scans_created_at     ON scans(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_compliance     ON scans(compliance_result);
CREATE INDEX IF NOT EXISTS idx_violations_scan_id   ON violations(scan_id);
CREATE INDEX IF NOT EXISTS idx_violations_severity  ON violations(severity);
CREATE INDEX IF NOT EXISTS idx_violations_rule_code ON violations(rule_code);
CREATE INDEX IF NOT EXISTS idx_products_barcode     ON products(barcode);
CREATE INDEX IF NOT EXISTS idx_products_status      ON products(compliance_status);
CREATE INDEX IF NOT EXISTS idx_reports_user_id      ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id   ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created   ON audit_logs(created_at DESC);
"""

# ---------------------------------------------------------------------------
# updated_at trigger (auto-update on row modification)
# ---------------------------------------------------------------------------

CREATE_UPDATED_AT_TRIGGER = """
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'set_users_updated_at'
    ) THEN
        CREATE TRIGGER set_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END;
$$;
"""

# Existing installations created before all five roles were introduced need
# this migration as well as the fresh-install DDL above.
MIGRATE_USER_ROLES = """
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_id TEXT UNIQUE;
UPDATE users SET role = 'consumer' WHERE role = 'viewer';
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users
    ADD CONSTRAINT users_role_check
    CHECK (role IN ('admin','inspector','supervisor','manufacturer','consumer'));
"""

# ---------------------------------------------------------------------------
# Demo seed data
# ---------------------------------------------------------------------------

SEED_USERS = [
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "admin@legalmetro.gov.in")),
        "user_id": "admin",
        "supabase_user_id": None,
        "role": "admin",
        "name": "System Administrator",
        "email": "admin@legalmetro.gov.in",
        "mobile": "+919900000000",
        "organization": "Department of Consumer Affairs",
        "state": "Delhi",
        "designation": "System Admin",
        "gstin": None,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "rajesh.agarwal@inspector.gov.in")),
        "user_id": "rajesh.agarwal",
        "supabase_user_id": None,
        "role": "inspector",
        "name": "Rajesh Agarwal",
        "email": "rajesh.agarwal@legalmetro.gov.in",
        "mobile": "+919811000001",
        "organization": "Legal Metrology Department",
        "state": "Uttar Pradesh",
        "designation": "Inspector",
        "gstin": None,
    },
    {
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, "meera.krishnan@inspector.gov.in")),
        "user_id": "meera.krishnan",
        "supabase_user_id": None,
        "role": "supervisor",
        "name": "Meera Krishnan",
        "email": "meera.krishnan@legalmetro.gov.in",
        "mobile": "+919811000002",
        "organization": "Legal Metrology Department",
        "state": "Tamil Nadu",
        "designation": "Senior Inspector",
        "gstin": None,
    },
]

INSERT_SEED_USER = """
INSERT INTO users (id, user_id, supabase_user_id, role, name, email, mobile,
                   organization, state, designation, gstin)
VALUES (%(id)s, %(user_id)s, %(supabase_user_id)s, %(role)s, %(name)s, %(email)s,
        %(mobile)s, %(organization)s, %(state)s, %(designation)s, %(gstin)s)
ON CONFLICT (email) DO NOTHING;
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def init_database():
    conn = get_db_connection()
    try:
        with conn:
            cur = conn.cursor()

            print("Creating extensions...")
            cur.execute(CREATE_EXTENSIONS)

            print("Creating tables...")
            cur.execute(CREATE_USERS_TABLE)
            cur.execute(CREATE_PRODUCTS_TABLE)
            cur.execute(CREATE_SCANS_TABLE)
            cur.execute(CREATE_VIOLATIONS_TABLE)
            cur.execute(CREATE_REPORTS_TABLE)
            cur.execute(CREATE_AUDIT_LOGS_TABLE)

            print("Creating indexes...")
            cur.execute(CREATE_INDEXES)

            print("Creating triggers...")
            cur.execute(CREATE_UPDATED_AT_TRIGGER)

            print("Migrating role constraints...")
            cur.execute(MIGRATE_USER_ROLES)

            print("Migrating scans table (consumer_reported)...")
            cur.execute("""
                ALTER TABLE scans
                ADD COLUMN IF NOT EXISTS consumer_reported BOOLEAN NOT NULL DEFAULT FALSE;
            """)

            print("Seeding initial users...")
            for user in SEED_USERS:
                cur.execute(INSERT_SEED_USER, user)

            cur.close()

        print("Database initialisation complete.")
    except Exception as exc:
        print(f"Database initialisation failed: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
