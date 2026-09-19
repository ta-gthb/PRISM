#!/usr/bin/env python3
"""Safely manage System Administrator credentials in Supabase Auth and PostgreSQL.

Run from ``backend/`` with the production environment variables available:
    python scripts/manage_admin.py create --user-id state-admin --name "State Admin" \
      --email admin@example.gov.in --state Delhi

The command reads DATABASE_URL, SUPABASE_URL, and SUPABASE_SERVICE_KEY from
the environment (or backend/.env). Never pass a service-role key as a command
argument. Passwords are requested without echo when omitted from the command.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


STATE_CODES = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "00": "National / Central HQ",
}


def resolve_state(code_or_name: str) -> str:
    if not code_or_name:
        return "Delhi"
    val = code_or_name.strip()
    if val.isdigit():
        padded = val.zfill(2)
        if padded in STATE_CODES:
            return STATE_CODES[padded]
    val_lower = val.lower()
    for code, name in STATE_CODES.items():
        if val == code or val_lower == name.lower():
            return name
    return val


def display_state_codes():
    print("\nSelectable State Codes:")
    print("-" * 76)
    items = sorted(STATE_CODES.items(), key=lambda x: (x[0] == "00", x[0]))
    for i in range(0, len(items), 2):
        c1, s1 = items[i]
        col1 = f"  [{c1}] {s1}"
        if i + 1 < len(items):
            c2, s2 = items[i + 1]
            col2 = f"[{c2}] {s2}"
            print(f"{col1:<38} {col2}")
        else:
            print(col1)
    print("-" * 76)


def prompt_state_selection(default_code="07") -> str:
    display_state_codes()
    default_name = STATE_CODES.get(default_code, "Delhi")
    while True:
        prompt_str = f"Enter State Code (e.g. 19 for West Bengal) [{default_code} - {default_name}]: "
        raw = input(prompt_str).strip()
        if not raw:
            print(f"  -> State auto-allotted: {default_name} (Code: {default_code})\n")
            return default_name
        code_padded = raw.zfill(2) if raw.isdigit() else raw
        if code_padded in STATE_CODES:
            allocated = STATE_CODES[code_padded]
            print(f"  -> State auto-allotted: {allocated} (Code: {code_padded})\n")
            return allocated
        # Also allow typing state name directly
        matched = None
        for c, s in STATE_CODES.items():
            if raw.lower() == s.lower():
                matched = (c, s)
                break
        if matched:
            print(f"  -> State auto-allotted: {matched[1]} (Code: {matched[0]})\n")
            return matched[1]
        print(f"  [!] Invalid State Code '{raw}'. Please enter a valid code from the list above (e.g. 19 for West Bengal).")


def load_env_files():
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        load_dotenv()
    except Exception:
        pass
    # Fallback manual parser for .env files when python-dotenv is not installed
    for env_path in [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
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


def require_settings():
    load_env_files()
    from supabase import create_client

    url, key, database_url = (os.getenv(name) for name in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "DATABASE_URL"))
    if not url or not key or not database_url:
        raise RuntimeError("Set SUPABASE_URL, SUPABASE_SERVICE_KEY, and DATABASE_URL in backend/.env before running this command.")
    return create_client(url, key)


def find_admin(user_id):
    from db.connection import get_db_connection

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE user_id=%s AND role='admin'", (user_id,))
        row = cur.fetchone()
        if not row:
            raise RuntimeError("No System Administrator exists with that user ID.")
        return dict(row)
    finally:
        conn.close()


def prompt_input(label, default=None, required=True):
    prompt_str = f"{label} [{default}]: " if default else f"{label}: "
    while True:
        val = input(prompt_str).strip()
        if not val and default is not None:
            return default
        if not val and required:
            print("  [!] This field cannot be empty. Please try again.")
            continue
        return val if val else None


def prompt_password(confirm=True):
    while True:
        p1 = getpass.getpass("Password (min 8 chars): ")
        if len(p1) < 8:
            print("  [!] Password must be at least 8 characters long.")
            continue
        if confirm:
            p2 = getpass.getpass("Confirm password: ")
            if p1 != p2:
                print("  [!] Passwords do not match. Please try again.")
                continue
        return p1


def password_from_args(args, required=False):
    password = getattr(args, "password", None)
    if password is None and required:
        password = prompt_password(confirm=True)
    if password is not None and len(password) < 8:
        raise RuntimeError("Passwords must contain at least 8 characters.")
    return password


def create_admin(args):
    print("\n--- Create New System Administrator ---")
    if not getattr(args, "user_id", None):
        args.user_id = prompt_input("Admin User ID (e.g. admin)", default="admin")
    if not getattr(args, "name", None):
        args.name = prompt_input("Full Name", default="System Administrator")
    if not getattr(args, "email", None):
        args.email = prompt_input("Email address", default=f"{args.user_id}@prism.gov.in")

    # State: show selectable state codes (e.g. 19 for West Bengal) and auto-allot state
    if not getattr(args, "state", None):
        args.state = prompt_state_selection(default_code="07")
    else:
        args.state = resolve_state(args.state)

    # Organisation & Designation are auto-assigned without prompting user
    args.organization = getattr(args, "organization", None) or "DoCA"
    args.designation = getattr(args, "designation", None) or "System Administrator"
    print(f"  -> Organization: {args.organization} (Auto-assigned: Department of Consumer Affairs)")
    print(f"  -> Designation:  {args.designation} (Auto-assigned)\n")

    client = require_settings()
    password = password_from_args(args, required=True)
    created_auth_id = None
    is_new_auth_user = False
    try:
        try:
            auth_user = client.auth.admin.create_user({
                "email": args.email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": args.name,
                    "role": "admin",
                    "user_id": args.user_id,
                    "state": args.state,
                    "organization": args.organization,
                    "designation": args.designation,
                },
            }).user
            created_auth_id = str(auth_user.id)
            is_new_auth_user = True
        except Exception as auth_err:
            err_msg = str(auth_err).lower()
            if any(k in err_msg for k in ("already", "registered", "exists")):
                print(f"  [*] Notice: Email '{args.email}' already exists in Supabase Auth.")
                print(f"  [*] Updating credentials and syncing to existing auth account...")
                existing_auth_id = None
                from db.connection import get_db_connection
                try:
                    conn_tmp = get_db_connection()
                    try:
                        with conn_tmp.cursor() as c_tmp:
                            c_tmp.execute("SELECT id FROM auth.users WHERE LOWER(email) = LOWER(%s)", (args.email,))
                            row = c_tmp.fetchone()
                            if row:
                                existing_auth_id = str(row["id"] if isinstance(row, dict) else row[0])
                    finally:
                        conn_tmp.close()
                except Exception:
                    pass

                if not existing_auth_id:
                    try:
                        res = client.auth.admin.list_users()
                        u_list = getattr(res, "users", res) if not isinstance(res, list) else res
                        for u in u_list:
                            if getattr(u, "email", "").lower() == args.email.lower():
                                existing_auth_id = str(u.id)
                                break
                    except Exception:
                        pass

                if existing_auth_id:
                    client.auth.admin.update_user_by_id(
                        existing_auth_id,
                        {
                            "password": password,
                            "email_confirm": True,
                            "user_metadata": {
                                "full_name": args.name,
                                "role": "admin",
                                "user_id": args.user_id,
                                "state": args.state,
                                "organization": args.organization,
                                "designation": args.designation,
                            },
                        }
                    )
                    created_auth_id = existing_auth_id
                    is_new_auth_user = False
                else:
                    raise auth_err
            else:
                raise auth_err

        from db.connection import get_db_connection
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            # Ensure users created_at and updated_at are TIMESTAMPTZ if previously VARCHAR
            try:
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
            except Exception:
                pass

            # Check if user with same user_id OR email already exists in users table
            cur.execute("SELECT id, user_id, email FROM users WHERE user_id = %s OR LOWER(email) = LOWER(%s)", (args.user_id, args.email))
            existing_db_user = cur.fetchone()

            if existing_db_user:
                cur.execute("""
                    UPDATE users SET
                        user_id = %s,
                        supabase_user_id = %s,
                        role = 'admin',
                        name = %s,
                        email = %s,
                        state = %s,
                        organization = %s,
                        designation = %s,
                        is_active = TRUE,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                """, (args.user_id, created_auth_id, args.name, args.email, args.state, args.organization, args.designation, existing_db_user["id"]))
            else:
                cur.execute("""
                    INSERT INTO users (user_id, supabase_user_id, role, name, email, state, organization, designation, created_at, updated_at)
                    VALUES (%s,%s,'admin',%s,%s,%s,%s,%s, NOW(), NOW())
                    RETURNING id
                """, (args.user_id, created_auth_id, args.name, args.email, args.state, args.organization, args.designation))

            # Also backfill in case any existing users have NULL created_at or updated_at
            try:
                cur.execute("UPDATE users SET created_at = NOW() WHERE created_at IS NULL")
                cur.execute("UPDATE users SET updated_at = NOW() WHERE updated_at IS NULL")
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()
    except Exception:
        if created_auth_id and is_new_auth_user:
            try:
                client.auth.admin.delete_user(created_auth_id)
            except Exception:
                pass
        raise
    print(f" Successfully created/updated System Administrator '{args.user_id}' ({args.email}) for jurisdiction: {args.state}.")


def update_admin(args):
    if not getattr(args, "user_id", None):
        args.user_id = prompt_input("Admin User ID to update")
    client = require_settings()
    admin = find_admin(args.user_id)

    # If all update flags were omitted, prompt interactively
    if not any([args.name, args.email, args.state, args.organization, args.designation, args.password]):
        print(f"\nEditing admin '{args.user_id}'. Press Enter to keep current values:")
        args.name = prompt_input("Full Name", default=admin.get("name"), required=False)
        args.email = prompt_input("Email", default=admin.get("email"), required=False)
        change_state = input(f"Current State: {admin.get('state')}. Change State? (y/N): ").strip().lower()
        if change_state in ("y", "yes"):
            args.state = prompt_state_selection()
        else:
            args.state = admin.get("state")
        args.organization = prompt_input("Organization", default=admin.get("organization") or "DoCA", required=False)
        args.designation = prompt_input("Designation", default=admin.get("designation") or "System Administrator", required=False)
        change_pw = input("Change password? (y/N): ").strip().lower()
        if change_pw in ("y", "yes"):
            args.password = prompt_password(confirm=True)

    if getattr(args, "state", None):
        args.state = resolve_state(args.state)

    password = password_from_args(args)
    changes = {key: value for key, value in {"name": args.name, "email": args.email, "state": args.state, "organization": args.organization, "designation": args.designation}.items() if value is not None}
    if not changes and password is None:
        raise RuntimeError("Supply at least one change.")
    auth_changes = {}
    if args.email:
        auth_changes["email"] = args.email
    if password:
        auth_changes["password"] = password
    user_metadata = {}
    if args.name:
        user_metadata["full_name"] = args.name
    if args.state:
        user_metadata["state"] = args.state
    if args.organization:
        user_metadata["organization"] = args.organization
    if args.designation:
        user_metadata["designation"] = args.designation
    if user_metadata:
        auth_changes["user_metadata"] = user_metadata
    if auth_changes:
        client.auth.admin.update_user_by_id(admin["supabase_user_id"], auth_changes)
    if changes:
        from db.connection import get_db_connection
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            assignments = ", ".join(f"{key}=%s" for key in changes)
            cur.execute(f"UPDATE users SET {assignments}, updated_at=NOW() WHERE id=%s", [*changes.values(), admin["id"]])
            conn.commit()
        finally:
            conn.close()
    print(f" Updated System Administrator '{args.user_id}'.")


def set_admin_active(args, active):
    if not getattr(args, "user_id", None):
        action = "enable" if active else "disable"
        args.user_id = prompt_input(f"Admin User ID to {action}")
    client = require_settings()
    admin = find_admin(args.user_id)
    client.auth.admin.update_user_by_id(admin["supabase_user_id"], {"ban_duration": "none" if active else "876000h"})
    from db.connection import get_db_connection
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_active=%s, updated_at=NOW() WHERE id=%s", (active, admin["id"]))
        conn.commit()
    finally:
        conn.close()
    print(f" {'Enabled' if active else 'Disabled'} System Administrator '{args.user_id}'.")


def delete_admin(args):
    if not getattr(args, "user_id", None):
        args.user_id = prompt_input("Admin User ID to permanently delete")
    if not getattr(args, "confirm_delete", None):
        print(f" [!] Warning: This will permanently delete admin '{args.user_id}' from Supabase Auth and the Database.")
        args.confirm_delete = prompt_input(f"Type '{args.user_id}' to confirm deletion")
    if args.confirm_delete != args.user_id:
        raise RuntimeError("Permanent deletion cancelled: confirmation did not match user ID.")
    client = require_settings()
    admin = find_admin(args.user_id)
    client.auth.admin.delete_user(admin["supabase_user_id"])
    from db.connection import get_db_connection
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=%s AND role='admin'", (admin["id"],))
        conn.commit()
    finally:
        conn.close()
    print(f" Permanently deleted System Administrator '{args.user_id}'.")


def interactive_menu():
    print("\n" + "=" * 56)
    print("       PRISM System Administrator Management Wizard")
    print("=" * 56)
    print(" 1) Create new Admin account")
    print(" 2) Update existing Admin account")
    print(" 3) Disable Admin account")
    print(" 4) Enable Admin account")
    print(" 5) Delete Admin account permanently")
    print(" 6) Exit")
    print("=" * 56)

    choice = input("Select an option [1-6]: ").strip()
    if choice == "1":
        class DummyArgs:
            command = "create"
            user_id = None
            name = None
            email = None
            state = None
            organization = None
            designation = None
            password = None
        create_admin(DummyArgs())
    elif choice == "2":
        class DummyArgs:
            command = "update"
            user_id = None
            name = None
            email = None
            state = None
            organization = None
            designation = None
            password = None
        update_admin(DummyArgs())
    elif choice == "3":
        class DummyArgs:
            user_id = None
        set_admin_active(DummyArgs(), False)
    elif choice == "4":
        class DummyArgs:
            user_id = None
        set_admin_active(DummyArgs(), True)
    elif choice == "5":
        class DummyArgs:
            user_id = None
            confirm_delete = None
        delete_admin(DummyArgs())
    elif choice in ("6", "q", "exit", ""):
        print("Exiting.")
        return
    else:
        print("[!] Invalid option. Please select 1-6.")


def parser():
    root = argparse.ArgumentParser(description="Manage deployed PRISM System Administrator accounts.")
    commands = root.add_subparsers(dest="command", required=False)
    create = commands.add_parser("create", help="Create an admin in Supabase Auth and PostgreSQL")
    create.add_argument("--user-id", default=None)
    create.add_argument("--name", default=None)
    create.add_argument("--email", default=None)
    create.add_argument("--state", default=None, help="State name or 2-digit code (e.g. 19 for West Bengal, 07 for Delhi)")
    create.add_argument("--organization", default="DoCA", help="Organization name (defaults to DoCA)")
    create.add_argument("--designation", default="System Administrator", help="Designation (defaults to System Administrator)")
    create.add_argument("--password", help="Avoid shell history; omit to enter securely.")
    update = commands.add_parser("update", help="Update an existing admin")
    update.add_argument("--user-id", default=None)
    update.add_argument("--name", default=None)
    update.add_argument("--email", default=None)
    update.add_argument("--state", default=None)
    update.add_argument("--organization", default=None)
    update.add_argument("--designation", default=None)
    update.add_argument("--password", default=None)
    for name, help_text in (("disable", "Disable an admin without deleting records"), ("enable", "Re-enable a disabled admin")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--user-id", default=None)
    delete = commands.add_parser("delete", help="Permanently delete an admin from Auth and PostgreSQL")
    delete.add_argument("--user-id", default=None)
    delete.add_argument("--confirm-delete", default=None)
    return root


if __name__ == "__main__":
    if len(sys.argv) == 1:
        try:
            interactive_menu()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)
        except Exception as error:
            print(f"\nError: {error}", file=sys.stderr)
            sys.exit(1)
    else:
        args = parser().parse_args()
        if not args.command:
            interactive_menu()
            sys.exit(0)
        try:
            {"create": create_admin, "update": update_admin, "disable": lambda a: set_admin_active(a, False), "enable": lambda a: set_admin_active(a, True), "delete": delete_admin}[args.command](args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)
        except Exception as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)
