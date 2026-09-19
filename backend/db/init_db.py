"""
Database initialisation script.

Run directly:  python db/init_db.py
Or called as part of the Render build command.

Creates all tables (idempotent — uses CREATE TABLE IF NOT EXISTS) and seeds
seed users so the system is usable immediately after first deploy.
"""

import os
import sys
from pathlib import Path

# Ensure backend root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
    load_dotenv()
except Exception:
    pass

for env_file in [BASE_DIR / ".env", BASE_DIR.parent / ".env", Path(".env")]:
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

try:
    from db.connection import get_db_connection
except ImportError:
    from connection import get_db_connection

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

CREATE_SCAN_EVIDENCE_TABLE = """
CREATE TABLE IF NOT EXISTS scan_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    file_name TEXT NOT NULL,
    content_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_CONSUMER_CASES_TABLE = """
CREATE TABLE IF NOT EXISTS consumer_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID NOT NULL UNIQUE REFERENCES scans(id) ON DELETE CASCADE,
    state TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','under_review','resolved','closed')),
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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

CREATE_RULE_CONFIG_TABLE = """
CREATE TABLE IF NOT EXISTS rule_config (
    rule_code TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical','major','minor')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_STATE_RULE_THRESHOLDS_TABLE = """
CREATE TABLE IF NOT EXISTS state_rule_thresholds (
    state TEXT PRIMARY KEY,
    critical_threshold INT NOT NULL DEFAULT 40,
    major_threshold INT NOT NULL DEFAULT 65,
    auto_flag_below INT NOT NULL DEFAULT 50,
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
CREATE INDEX IF NOT EXISTS idx_evidence_scan_id      ON scan_evidence(scan_id);
CREATE INDEX IF NOT EXISTS idx_cases_state_status    ON consumer_cases(state, status);
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

def ensure_users_schema(cur):
    """Ensure public.users table exists, has id as UUID, and has all expected columns."""
    cur.execute("""
        SELECT data_type, udt_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'id';
    """)
    row = cur.fetchone()
    if row:
        udt_name = str(row["udt_name"] if isinstance(row, dict) else row[1]).lower()
        if udt_name != "uuid":
            print(f"Migrating public.users.id from '{udt_name}' to 'uuid'...")
            # Drop any foreign key constraints pointing to users(id) from any other table
            cur.execute("""
                SELECT conname, conrelid::regclass::text AS relname
                FROM pg_constraint
                WHERE confrelid = 'public.users'::regclass AND contype = 'f';
            """)
            fks = cur.fetchall()
            for r in fks:
                fk_name = r["conname"] if isinstance(r, dict) else r[0]
                rel_name = r["relname"] if isinstance(r, dict) else r[1]
                cur.execute(f'ALTER TABLE {rel_name} DROP CONSTRAINT IF EXISTS "{fk_name}";')

            # Ensure user_id column exists
            cur.execute("ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_id TEXT;")
            cur.execute("UPDATE public.users SET user_id = id::text WHERE user_id IS NULL AND id IS NOT NULL;")

            # Drop primary key constraint on users
            cur.execute("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'public.users'::regclass AND contype = 'p';
            """)
            pk_rows = cur.fetchall()
            for pk in pk_rows:
                pk_name = pk["conname"] if isinstance(pk, dict) else pk[0]
                cur.execute(f'ALTER TABLE public.users DROP CONSTRAINT IF EXISTS "{pk_name}";')

            # Drop existing default if any
            cur.execute("ALTER TABLE public.users ALTER COLUMN id DROP DEFAULT;")

            # For rows with non-UUID strings, generate new UUIDs
            cur.execute("""
                UPDATE public.users 
                SET id = gen_random_uuid()::text 
                WHERE id::text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
            """)

            # Alter column to UUID
            cur.execute("ALTER TABLE public.users ALTER COLUMN id TYPE UUID USING id::uuid;")
            cur.execute("ALTER TABLE public.users ALTER COLUMN id SET DEFAULT gen_random_uuid();")
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conrelid = 'public.users'::regclass AND contype = 'p'
                    ) THEN
                        ALTER TABLE public.users ADD PRIMARY KEY (id);
                    END IF;
                END;
                $$;
            """)
            print("public.users.id successfully migrated to UUID.")

    # Ensure all required columns exist on users
    cur.execute("""
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS user_id TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS supabase_user_id TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'inspector';
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS email TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS mobile TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS organization TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS state TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS designation TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS gstin TEXT;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'created_at' 
                AND data_type IN ('character varying', 'varchar', 'text')
            ) THEN
                BEGIN
                    ALTER TABLE public.users ALTER COLUMN created_at TYPE TIMESTAMPTZ USING COALESCE(NULLIF(created_at, '')::timestamptz, NOW());
                    ALTER TABLE public.users ALTER COLUMN created_at SET DEFAULT NOW();
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'updated_at' 
                AND data_type IN ('character varying', 'varchar', 'text')
            ) THEN
                BEGIN
                    ALTER TABLE public.users ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING COALESCE(NULLIF(updated_at, '')::timestamptz, NOW());
                    ALTER TABLE public.users ALTER COLUMN updated_at SET DEFAULT NOW();
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END;
        $$;
    """)
    cur.execute("""
        UPDATE public.users SET created_at = NOW() WHERE created_at IS NULL;
        UPDATE public.users SET updated_at = NOW() WHERE updated_at IS NULL;
    """)
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'users_user_id_key'
            ) THEN
                BEGIN
                    ALTER TABLE public.users ADD CONSTRAINT users_user_id_key UNIQUE (user_id);
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'users_supabase_user_id_key'
            ) THEN
                BEGIN
                    ALTER TABLE public.users ADD CONSTRAINT users_supabase_user_id_key UNIQUE (supabase_user_id);
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END;
        $$;
    """)


def ensure_audit_logs_schema(cur):
    """Ensure audit_logs table has all expected columns."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.audit_logs (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id    UUID REFERENCES users(id) ON DELETE SET NULL,
            action     TEXT,
            resource   TEXT,
            details    JSONB NOT NULL DEFAULT '{}',
            ip_address INET,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS user_id UUID;
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS action TEXT;
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS resource TEXT;
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS details JSONB NOT NULL DEFAULT '{}';
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS ip_address INET;
        ALTER TABLE public.audit_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def init_database():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("WARNING: DATABASE_URL environment variable is not set. Skipping schema initialization.")
        return

    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"WARNING: Could not connect to database ({e}). Schema initialization will be skipped.")
        return

    try:
        with conn:
            cur = conn.cursor()

            print("Creating extensions...")
            cur.execute(CREATE_EXTENSIONS)

            print("Creating tables...")
            cur.execute(CREATE_USERS_TABLE)
            ensure_users_schema(cur)
            cur.execute(CREATE_PRODUCTS_TABLE)
            cur.execute(CREATE_SCANS_TABLE)
            cur.execute(CREATE_SCAN_EVIDENCE_TABLE)
            cur.execute(CREATE_CONSUMER_CASES_TABLE)
            cur.execute(CREATE_VIOLATIONS_TABLE)
            cur.execute(CREATE_REPORTS_TABLE)
            cur.execute(CREATE_AUDIT_LOGS_TABLE)
            ensure_audit_logs_schema(cur)
            cur.execute(CREATE_RULE_CONFIG_TABLE)
            cur.execute(CREATE_STATE_RULE_THRESHOLDS_TABLE)

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

            cur.close()

        print("Database initialisation complete.")
    except Exception as exc:
        print(f"Database initialisation failed: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
