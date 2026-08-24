#!/usr/bin/env python3
"""
add_instana_user.py
-------------------
Bulk-invite Instana users from a CSV file using the Instana REST API.

Endpoint: POST /api/settings/invitation/share

CSV format (header row required):
  email,fullName,role,groupId

  - role     must be one of: ADMIN, USER, VIEWER  (default: USER if omitted)
  - groupId  RBAC group to assign; use "-1" for no specific group (default: -1)

Usage:
  # copy and fill in your credentials
  cp .env.example .env
  source .env                        # Linux/macOS
  # -- or on Windows PowerShell --
  # $env:INSTANA_BASE_URL = "https://..."
  # $env:INSTANA_API_TOKEN = "..."

  python add_instana_user.py users.csv

Optional flags:
  --dry-run        Print what would be sent without calling the API.
  --log FILE       Write a detailed JSON log to FILE (default: invite_log.json)
  --no-log         Disable log file output entirely.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

import requests

# ── Configuration ──────────────────────────────────────────────────────────────

VALID_ROLES = {"ADMIN", "USER", "VIEWER"}
DEFAULT_ROLE = "USER"


def get_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Environment variable {name} is required.", file=sys.stderr)
        sys.exit(1)
    return value


# ── Instana API call ───────────────────────────────────────────────────────────

def invite_user(base_url: str, api_token: str, email: str,
                full_name: str, role: str, group_id: str = "-1") -> dict:
    """
    POST /api/settings/invitation/share
    Returns the parsed JSON response (or {} on 204 No Content).
    Raises RuntimeError on HTTP error.
    """
    url = f"{base_url}/api/settings/invitation/share"
    headers = {
        "authorization": f"apiToken {api_token}",
        "content-type": "application/json",
        "accept": "application/json",
    }
    payload = json.dumps([{
        "email": email,
        "fullName": full_name,
        "permissionSet": role,
        "groupId": group_id,
    }])

    response = requests.post(url, data=payload, headers=headers, verify=False)

    if not response.ok:
        raise RuntimeError(
            f"HTTP {response.status_code} {response.reason}: {response.text}"
        )

    return response.json() if response.text.strip() else {}


# ── CSV parsing ────────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    """
    Parse the CSV and return a list of normalised user dicts.
    Required columns: email, fullName
    Optional columns: role (defaults to USER), groupId (defaults to -1)
    """
    users = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"email", "fullName"}
        if not required.issubset(set(reader.fieldnames or [])):
            missing = required - set(reader.fieldnames or [])
            print(
                f"ERROR: CSV is missing required column(s): {', '.join(sorted(missing))}",
                file=sys.stderr,
            )
            sys.exit(1)

        for line_num, row in enumerate(reader, start=2):
            email     = row["email"].strip()
            full_name = row["fullName"].strip()
            role      = row.get("role", "").strip().upper() or DEFAULT_ROLE
            group_id  = row.get("groupId", "").strip() or "-1"

            if not email:
                print(f"  [line {line_num}] WARNING: empty email — skipping.")
                continue
            if role not in VALID_ROLES:
                print(
                    f"  [line {line_num}] WARNING: invalid role '{role}' "
                    f"for {email} — defaulting to {DEFAULT_ROLE}."
                )
                role = DEFAULT_ROLE

            users.append({"email": email, "full_name": full_name, "role": role, "group_id": group_id})

    return users


# ── Logging ────────────────────────────────────────────────────────────────────

def save_log(log_path: str, entries: list[dict]) -> None:
    """Write all invite results to a JSON log file."""
    log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "succeeded": sum(1 for e in entries if e["status"] == "OK"),
        "failed": sum(1 for e in entries if e["status"] != "OK"),
        "results": entries,
    }
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
    print(f"\nLog saved to: {log_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-invite Instana users from a CSV.")
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without calling the API")
    parser.add_argument("--log", default="invite_log.json", metavar="FILE",
                        help="Path for the JSON log file (default: invite_log.json)")
    parser.add_argument("--no-log", action="store_true",
                        help="Disable log file output entirely")
    args = parser.parse_args()

    base_url  = get_env("INSTANA_BASE_URL").rstrip("/")
    api_token = get_env("INSTANA_API_TOKEN")

    users = load_csv(args.csv_file)
    if not users:
        print("No valid users found in CSV. Nothing to do.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Inviting {len(users)} user(s)...\n")

    ok = failed = 0
    log_entries: list[dict] = []

    for user in users:
        label = f"{user['full_name']} <{user['email']}> role={user['role']} groupId={user['group_id']}"
        entry: dict = {
            "email":    user["email"],
            "fullName": user["full_name"],
            "role":     user["role"],
            "groupId":  user["group_id"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if args.dry_run:
            print(f"  [DRY RUN] Would invite: {label}")
            entry["status"] = "DRY_RUN"
            ok += 1
        else:
            try:
                resp = invite_user(base_url, api_token,
                                   email=user["email"],
                                   full_name=user["full_name"],
                                   role=user["role"],
                                   group_id=user["group_id"])
                print(f"  [OK] Invited: {label}")
                entry["status"]   = "OK"
                entry["response"] = resp
                ok += 1
            except RuntimeError as exc:
                err = str(exc)
                print(f"  [FAIL] {label}\n     {err}")
                entry["status"] = "FAIL"
                entry["error"]  = err
                failed += 1

        log_entries.append(entry)

    print(f"\nDone. {ok} succeeded, {failed} failed.")

    if not args.no_log:
        save_log(args.log, log_entries)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
