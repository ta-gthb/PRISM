#!/usr/bin/env python3
"""Database management and reinitialization utility for PRISM.

Can be run locally from device or in deployment environments:
    python reinit_db.py
    python reinit_db.py --sync
    python reinit_db.py --clean
    python reinit_db.py --status
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def load_env_files():
    """Load environment variables from .env files or prompt."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        load_dotenv(BASE_DIR.parent / ".env")
        load_dotenv()
    except Exception:
        pass

    for env_path in [
        BASE_DIR / ".env",
        BASE_DIR.parent / ".env",
        Path(".env"),
    ]:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass


def get_connection(override_url=None):
    """Return a psycopg2 connection, prompting for DATABASE_URL if missing."""
    load_env_files()
    db_url = override_url or os.getenv("DATABASE_URL")

    if not db_url:
        print("\n[!] DATABASE_URL environment variable is not set.")
        db_url = input("Enter PostgreSQL DATABASE_URL (e.g. postgresql://postgres:...@.../postgres): ").strip()
        if not db_url:
            raise RuntimeError("Database URL is required to proceed.")
        save = input("Save this DATABASE_URL to backend/.env? (y/N): ").strip().lower()
        if save in ("y", "yes"):
            env_file = BASE_DIR / ".env"
            with open(env_file, "a", encoding="utf-8") as f:
                f.write(f"\nDATABASE_URL=\"{db_url}\"\n")
            print(f"[✓] Saved DATABASE_URL to {env_file}")
        os.environ["DATABASE_URL"] = db_url

    import psycopg2
    from psycopg2.extras import RealDictCursor
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def safe_schema_sync(conn):
    """Run idempotent schema creation and safe column migrations."""
    from db.init_db import (
        CREATE_EXTENSIONS,
        CREATE_USERS_TABLE,
        ensure_users_schema,
        CREATE_PRODUCTS_TABLE,
        CREATE_SCANS_TABLE,
        CREATE_SCAN_EVIDENCE_TABLE,
        CREATE_CONSUMER_CASES_TABLE,
        CREATE_VIOLATIONS_TABLE,
        CREATE_REPORTS_TABLE,
        CREATE_AUDIT_LOGS_TABLE,
        ensure_audit_logs_schema,
        CREATE_RULE_CONFIG_TABLE,
        CREATE_INDEXES,
        CREATE_UPDATED_AT_TRIGGER,
        MIGRATE_USER_ROLES,
    )

    print("\n--- Running Safe Schema Sync ---")
    with conn:
        cur = conn.cursor()

        print("[1/8] Verifying PostgreSQL extensions...")
        cur.execute(CREATE_EXTENSIONS)

        print("[2/8] Ensuring core tables exist...")
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

        print("[3/8] Verifying indexes...")
        cur.execute(CREATE_INDEXES)

        print("[4/8] Configuring triggers...")
        cur.execute(CREATE_UPDATED_AT_TRIGGER)

        print("[5/8] Migrating user role constraints...")
        cur.execute(MIGRATE_USER_ROLES)

        print("[6/8] Migrating consumer reporting flags...")
        cur.execute("""
            ALTER TABLE scans
            ADD COLUMN IF NOT EXISTS consumer_reported BOOLEAN NOT NULL DEFAULT FALSE;
        """)

        print("[7/8] Ensuring timestamp data types are valid TIMESTAMPTZ...")
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

        print("[8/8] Backfilling missing timestamps...")
        cur.execute("UPDATE public.users SET created_at = NOW() WHERE created_at IS NULL;")
        cur.execute("UPDATE public.users SET updated_at = NOW() WHERE updated_at IS NULL;")

        cur.close()

    print("\n[✓] Safe Schema Sync completed successfully! All data has been preserved.")


def clean_rebuild_database(conn):
    """Drop and recreate all PRISM application tables."""
    print("\n" + "!" * 64)
    print(" WARNING: FRESH DATABASE REBUILD")
    print(" This operation will permanently DROP and RECREATE all PRISM tables:")
    print("   - scan_evidence")
    print("   - violations")
    print("   - consumer_cases")
    print("   - reports")
    print("   - audit_logs")
    print("   - scans")
    print("   - products")
    print("   - rule_config")
    print("   - users")
    print("!" * 64)

    confirmation = input("\nType 'REINIT' in capital letters to confirm: ").strip()
    if confirmation != "REINIT":
        print("[!] Aborted. No changes were made.")
        return False

    with conn:
        cur = conn.cursor()
        print("\n[1/3] Dropping existing PRISM tables in dependency order...")
        tables = [
            "scan_evidence",
            "violations",
            "consumer_cases",
            "reports",
            "audit_logs",
            "scans",
            "products",
            "rule_config",
            "users",
        ]
        for tbl in tables:
            cur.execute(f"DROP TABLE IF EXISTS public.{tbl} CASCADE;")
            print(f"   -> Dropped table {tbl}")

        cur.close()

    print("[2/3] Recreating fresh schema...")
    safe_schema_sync(conn)

    print("[3/3] Seeding default rule configurations...")
    seed_default_rules(conn)

    print("\nDo you also want to purge Supabase Auth accounts (auth.users)?")
    print("This ensures existing emails (e.g. admin, inspectors) can be registered afresh without 'email already exists' errors.")
    auth_choice = input("Purge Supabase Auth users? (y/N): ").strip().lower()
    if auth_choice in ("y", "yes"):
        purge_supabase_auth_users(conn)

    print("\n[✓] Full Database Rebuild completed successfully!")
    return True


def purge_supabase_auth_users(conn):
    """Purge registered users from Supabase Auth so emails can be registered afresh."""
    print("\n--- Purging Supabase Auth Users ---")
    print("This will remove user records from the Supabase Authentication service (auth.users).")

    cleared = False
    # 1. Try SQL truncate or delete on auth.users if permissions allow
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM auth.users;")
            cleared_count = cur.rowcount
            cur.close()
            print(f"[✓] Deleted {cleared_count} accounts from auth.users via direct database connection.")
            cleared = True
    except Exception as sql_exc:
        print(f"[*] Direct SQL delete on auth.users failed: {sql_exc}")
        print("[*] Attempting deletion via Supabase Management Admin API...")

    # 2. Try Admin API using SUPABASE_URL and SUPABASE_SERVICE_KEY
    if not cleared:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if url and key:
            try:
                from supabase import create_client
                sb_client = create_client(url, key)
                users_res = sb_client.auth.admin.list_users()
                u_list = getattr(users_res, "users", users_res) if not isinstance(users_res, list) else users_res
                count = 0
                for u in u_list:
                    try:
                        sb_client.auth.admin.delete_user(u.id)
                        count += 1
                    except Exception as de:
                        print(f"   Failed to delete {getattr(u, 'email', u.id)}: {de}")
                print(f"[✓] Deleted {count} user accounts via Supabase Admin API.")
                cleared = True
            except Exception as api_exc:
                print(f"[*] Supabase Admin API deletion failed: {api_exc}")

    if not cleared:
        print("[!] Notice: To clear auth users manually in the Supabase Dashboard:")
        print("    Go to Supabase Project -> Authentication -> Users -> Select all -> Delete.")
    return cleared


def seed_default_rules(conn):
    """Seed initial rule configuration entries."""
    print("\n--- Seeding Default Rule Configurations ---")
    rules = [
        ("MFR_DETAILS", "Manufacturer name and address must be clearly declared", "critical"),
        ("NET_QTY", "Net quantity declaration in standard units (g, kg, ml, l, etc.)", "critical"),
        ("MRP", "Maximum Retail Price inclusive of all taxes must be declared", "critical"),
        ("DATES", "Date of manufacture, packing, and/or expiry must be declared", "critical"),
        ("CONSUMER_CARE", "Consumer care telephone number and email/address must be declared", "major"),
        ("COUNTRY_OF_ORIGIN", "Country of origin for imported goods", "major"),
        ("COMMODITY_NAME", "Generic or common name of the commodity inside package", "major"),
        ("FONT_SIZE", "Declarations must meet minimum font size requirements based on net quantity", "minor"),
        ("LABEL_LANGUAGE", "Declarations must be in Hindi or English", "minor"),
    ]
    with conn:
        cur = conn.cursor()
        for code, desc, severity in rules:
            cur.execute("""
                INSERT INTO rule_config (rule_code, description, severity, is_active, updated_at)
                VALUES (%s, %s, %s, TRUE, NOW())
                ON CONFLICT (rule_code) DO UPDATE SET
                    description = EXCLUDED.description,
                    severity = EXCLUDED.severity,
                    is_active = TRUE,
                    updated_at = NOW();
            """, (code, desc, severity))
        cur.close()
    print(f"[✓] Successfully seeded/updated {len(rules)} legal rules in rule_config.")


def show_database_status(conn):
    """Display connection status and table statistics."""
    print("\n--- Database Status & Diagnostics ---")
    tables = [
        "users",
        "products",
        "scans",
        "scan_evidence",
        "violations",
        "consumer_cases",
        "reports",
        "audit_logs",
        "rule_config",
    ]
    cur = conn.cursor()
    try:
        cur.execute("SELECT version();")
        ver = cur.fetchone()
        v_str = ver["version"] if isinstance(ver, dict) else ver[0]
        print(f"PostgreSQL Version: {v_str.split(',')[0]}")

        print("\nTable Summary:")
        print("-" * 60)
        print(f"{'Table Name':<25} {'Exists?':<12} {'Row Count':<12}")
        print("-" * 60)
        for tbl in tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                ) AS exists;
            """, (tbl,))
            row = cur.fetchone()
            exists = row["exists"] if isinstance(row, dict) else row[0]
            if exists:
                cur.execute(f"SELECT COUNT(*) AS count FROM public.{tbl};")
                c_row = cur.fetchone()
                cnt = c_row["count"] if isinstance(c_row, dict) else c_row[0]
                print(f"{tbl:<25} {'YES':<12} {cnt:<12}")
            else:
                print(f"{tbl:<25} {'NO':<12} {'-':<12}")
        print("-" * 60)

        # Check users column types
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users' 
            AND column_name IN ('id', 'created_at', 'updated_at');
        """)
        cols = cur.fetchall()
        if cols:
            print("\nUsers Column Diagnostics:")
            for col in cols:
                cname = col["column_name"] if isinstance(col, dict) else col[0]
                dtype = col["data_type"] if isinstance(col, dict) else col[1]
                print(f"  • {cname}: {dtype}")
    finally:
        cur.close()


def run_interactive_wizard(conn):
    """Interactive CLI menu."""
    while True:
        print("\n" + "=" * 58)
        print("          PRISM Database Management & Setup Wizard")
        print("=" * 58)
        print(" 1) Safe Schema Sync (Apply migrations, add tables/columns)")
        print(" 2) Fresh Database Rebuild (Drop and recreate all PRISM tables)")
        print(" 3) Seed Default Rule Configuration")
        print(" 4) Check Database Health & Diagnostics")
        print(" 5) Purge Supabase Auth Accounts (Clear registered emails)")
        print(" 6) Exit")
        print("=" * 58)
        choice = input("Select an option [1-6]: ").strip()

        if choice == "1":
            safe_schema_sync(conn)
        elif choice == "2":
            clean_rebuild_database(conn)
        elif choice == "3":
            seed_default_rules(conn)
        elif choice == "4":
            show_database_status(conn)
        elif choice == "5":
            purge_supabase_auth_users(conn)
        elif choice in ("6", "q", "exit"):
            print("\nExiting Database Wizard. Goodbye!\n")
            break
        else:
            print("[!] Invalid option. Please enter a number between 1 and 6.")


def main():
    parser = argparse.ArgumentParser(description="Manage and reinitialize PRISM PostgreSQL database.")
    parser.add_argument("--database-url", default=None, help="PostgreSQL connection string")
    parser.add_argument("--sync", action="store_true", help="Run safe schema sync (non-destructive)")
    parser.add_argument("--clean", action="store_true", help="Fresh database rebuild (drop and recreate tables)")
    parser.add_argument("--clean-auth", action="store_true", help="Purge registered users from Supabase Auth")
    parser.add_argument("--seed", action="store_true", help="Seed default rule configuration")
    parser.add_argument("--status", action="store_true", help="Check database connection and table status")

    args = parser.parse_args()

    try:
        conn = get_connection(args.database_url)
    except Exception as exc:
        print(f"\n[!] Connection Error: {exc}\n")
        sys.exit(1)

    try:
        if args.clean_auth:
            purge_supabase_auth_users(conn)
        elif args.clean:
            clean_rebuild_database(conn)
        elif args.sync:
            safe_schema_sync(conn)
        elif args.seed:
            seed_default_rules(conn)
        elif args.status:
            show_database_status(conn)
        else:
            run_interactive_wizard(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
