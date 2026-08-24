#!/usr/bin/env python3
"""
create_application.py
=====================
Creates a new Application Perspective in Instana using tag-based service
matching rules.  All configuration is read from inputs.env.

Usage:
    1. Fill in inputs.env  (INSTANA_TOKEN, APP_NAME, APP_TAGS are required)
    2. python3 create_application.py

Flow:
    1. Load + validate inputs.env
    2. POST /api/settings/api-tokens  (apiToken auth)
         → create a full-permission token; supply caller-generated UUIDs for
           accessGrantingToken and internalId (required by this Instana version)
    3. POST /api/application-monitoring/settings/application  (new token)
    4. DELETE /api/settings/api-tokens/{internalId}  → clean up the lab token
    5. Print the new application ID on success

Reference:
    POST /api/application-monitoring/settings/application
    https://developer.ibm.com/apis/catalog/instana--instana-rest-api/api/API--instana--instana-rest-api-documentation#addApplicationConfig
"""

import json
import pathlib
import sys
import urllib.error
import urllib.request
import ssl
import uuid


# ---------------------------------------------------------------------------
# Load inputs.env
# ---------------------------------------------------------------------------
def load_inputs_env() -> dict[str, str]:
    env_file = pathlib.Path(__file__).parent / "inputs.env"
    if not env_file.exists():
        print(f"[ERROR] inputs.env not found at {env_file}", file=sys.stderr)
        sys.exit(1)

    values: dict[str, str] = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


# ---------------------------------------------------------------------------
# Parse APP_TAGS → list of matchingRule objects
# ---------------------------------------------------------------------------
def parse_tags(raw: str) -> list[dict]:
    rules = []
    for segment in raw.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        if "=" not in segment:
            print(f"[WARN] Skipping invalid tag segment (expected key=value): '{segment}'")
            continue
        key, _, value = segment.partition("=")
        rules.append({
            "key":      key.strip(),
            "value":    value.strip(),
            "operator": "EQUALS",
            "entity":   "DESTINATION",
        })
    return rules


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------
def _request(
    method: str,
    url: str,
    token: str,
    payload: list | dict | None = None,
) -> tuple[int, object]:
    """Returns (status_code, parsed_body). Uses apiToken auth."""
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url=url,
        data=body,
        method=method,
        headers={
            "Authorization": f"apiToken {token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
    )
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, (json.loads(raw) if raw else {"error": exc.reason})
    except urllib.error.URLError as exc:
        print(f"[ERROR] Could not reach {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Full permission set — exact field names from this Instana version
# ---------------------------------------------------------------------------
def _all_permissions() -> dict:
    return {
        "canConfigureServiceMapping":                     True,
        "canConfigureEumApplications":                    True,
        "canConfigureMobileAppMonitoring":                True,
        "canConfigureUsers":                              True,
        "canInstallNewAgents":                            True,
        "canConfigureIntegrations":                       True,
        "canConfigureApiTokens":                          True,
        "canConfigurePersonalApiTokens":                  True,
        "canConfigureAgentRunMode":                       True,
        "canViewAuditLog":                                True,
        "canConfigureAgents":                             True,
        "canDownloadAgentConfiguration":                  True,
        "canConfigureAuthenticationMethods":              True,
        "canConfigureApplications":                       True,
        "canConfigureTeams":                              True,
        "canConfigureReleases":                           True,
        "canConfigureLogManagement":                      True,
        "canConfigureDatabaseManagement":                 True,
        "canCreatePublicCustomDashboards":                True,
        "canViewLogs":                                    True,
        "canViewTraceDetails":                            True,
        "canConfigureSessionSettings":                    True,
        "canConfigureGlobalAlertPayload":                 True,
        "canViewAccountAndBillingInformation":            True,
        "canEditAllAccessibleCustomDashboards":           True,
        "canConfigureAutomationActions":                  True,
        "canConfigureAutomationPolicies":                 True,
        "canRunAutomationActions":                        True,
        "canDeleteAutomationActionHistory":               True,
        "canConfigureSyntheticTests":                     True,
        "canConfigureSyntheticLocations":                 True,
        "canConfigureSyntheticCredentials":               True,
        "canViewSyntheticTests":                          True,
        "canViewSyntheticLocations":                      True,
        "canViewSyntheticTestResults":                    True,
        "canUseSyntheticCredentials":                     True,
        "canConfigureBizops":                             True,
        "canViewBusinessProcesses":                       True,
        "canViewBusinessProcessDetails":                  True,
        "canViewBusinessActivities":                      True,
        "canViewBizAlerts":                               True,
        "canDeleteLogs":                                  True,
        "canCreateHeapDump":                              True,
        "canCreateThreadDump":                            True,
        "canConfigureEventsAndAlerts":                    True,
        "canConfigureMaintenanceWindows":                 True,
        "canConfigureApplicationSmartAlerts":             True,
        "canConfigureWebsiteSmartAlerts":                 True,
        "canConfigureMobileAppSmartAlerts":               True,
        "canConfigureGlobalApplicationSmartAlerts":       True,
        "canConfigureGlobalSyntheticSmartAlerts":         True,
        "canConfigureGlobalInfraSmartAlerts":             True,
        "canConfigureGlobalLogSmartAlerts":               True,
        "canManuallyCloseIssue":                          True,
        "canViewLogVolume":                               True,
        "canConfigureLogRetentionPeriod":                 True,
        "canConfigureSubtraces":                          True,
        "canInvokeAlertChannel":                          True,
        "canConfigureLLM":                                True,
        "canConfigureAiAgents":                           True,
        "canConfigureApdex":                              True,
        "canConfigureCustomEntities":                     True,
        "canConfigureWebsiteConversions":                 True,
        "canConfigureIPFiltering":                        True,
        "canConfigureLLMModelPrice":                      True,
        "canConfigurePersonallyIdentifiableInformationMasking": True,
        "canConfigureServiceLevels":                      True,
        "canConfigureServiceLevelSmartAlerts":            True,
        "canConfigureServiceLevelCorrectionWindows":      True,
    }


# ---------------------------------------------------------------------------
# Step 1 — Create a full-permission lab token using the admin token
# ---------------------------------------------------------------------------
def generate_lab_token(base_url: str, admin_token: str, app_name: str) -> tuple[str, str]:
    """
    Creates a full-permission API token using apiToken auth.
    This Instana version requires the caller to supply both
    accessGrantingToken (the visible token value) and internalId as UUIDs.
    Returns (token_value, internal_id).
    """
    print("[1/4] Generating full-permission lab token ...")

    # Both IDs are caller-supplied UUIDs — Instana stores them as-is
    access_granting_token = str(uuid.uuid4()).replace("-", "")[:22]
    internal_id           = str(uuid.uuid4()).replace("-", "")[:22]

    payload = {
        "name":                 f"lab1b-{app_name[:20]}-token",
        "accessGrantingToken":  access_granting_token,
        "internalId":           internal_id,
        **_all_permissions(),
    }

    status, body = _request(
        "POST",
        f"{base_url}/api/settings/api-tokens",
        token=admin_token,
        payload=payload,
    )

    if status in (200, 201):
        # Prefer the server-returned values in case Instana normalises them
        token_val   = (body.get("accessGrantingToken") if isinstance(body, dict) else None) or access_granting_token
        returned_id = (body.get("internalId")          if isinstance(body, dict) else None) or internal_id
        print(f"       Lab token created (internalId: {returned_id})")
        return token_val, returned_id
    else:
        errors = body.get("errors") or body.get("message") or body.get("error") or json.dumps(body) if isinstance(body, dict) else str(body)
        print(f"[ERROR] Failed to create lab token — HTTP {status}: {errors}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 4 — Delete the lab token
# ---------------------------------------------------------------------------
def delete_lab_token(base_url: str, admin_token: str, internal_id: str) -> None:
    print(f"[4/4] Cleaning up lab token (internalId: {internal_id}) ...")
    status, _ = _request(
        "DELETE",
        f"{base_url}/api/settings/api-tokens/{internal_id}",
        token=admin_token,
    )
    if status in (200, 204):
        print("       Token deleted.")
    else:
        print(f"[WARN] Could not delete token (HTTP {status}) — delete it manually in the Instana UI.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Build the application config payload
# ---------------------------------------------------------------------------
def _tag_filter(rule: dict) -> dict:
    """Converts a parsed tag rule into a TAG_FILTER node."""
    return {
        "type":        "TAG_FILTER",
        "name":        rule["key"],
        "stringValue": rule["value"],
        "value":       rule["value"],
        "operator":    rule["operator"],
        "entity":      rule["entity"],
    }


def build_payload(app_name: str, matching_rules: list[dict], boundary_scope: str) -> dict:
    if len(matching_rules) == 1:
        tag_filter_expression = _tag_filter(matching_rules[0])
    else:
        tag_filter_expression = {
            "type":            "EXPRESSION",
            "logicalOperator": "AND",
            "elements":        [_tag_filter(r) for r in matching_rules],
        }

    return {
        "label":                 app_name,
        "scope":                 "INCLUDE_ALL_DOWNSTREAM",
        "boundaryScope":         boundary_scope,
        "tagFilterExpression":   tag_filter_expression,
        "accessRules": [
            {"accessType": "READ_WRITE", "relationType": "GLOBAL", "relatedId": None}
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    cfg = load_inputs_env()

    base_url       = cfg.get("INSTANA_URL", "")
    admin_token    = cfg.get("INSTANA_TOKEN", "")
    app_name       = cfg.get("APP_NAME", "")
    raw_tags       = cfg.get("APP_TAGS", "")
    boundary_scope = cfg.get("BOUNDARY_SCOPE", "ALL").upper()

    # Validate required fields
    missing = []
    if not base_url    or "<" in base_url:    missing.append("INSTANA_URL")
    if not admin_token or "<" in admin_token: missing.append("INSTANA_TOKEN")
    if not app_name    or "<" in app_name:    missing.append("APP_NAME")
    if not raw_tags    or "<" in raw_tags:    missing.append("APP_TAGS")
    if missing:
        print("[ERROR] Please fill in the following fields in inputs.env:", file=sys.stderr)
        for m in missing:
            print(f"        {m}", file=sys.stderr)
        sys.exit(1)

    base_url = base_url.rstrip("/")

    # Parse tags
    matching_rules = parse_tags(raw_tags)
    if not matching_rules:
        print("[ERROR] APP_TAGS produced no valid rules.  "
              "Use format: key=value  or  key1=value1;key2=value2", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print()
    print(f"Instana host     : {base_url}")
    print(f"Application name : {app_name}")
    print(f"Tag rules        : {len(matching_rules)}")
    for r in matching_rules:
        print(f"                   {r['key']} = {r['value']}")
    print(f"Boundary scope   : {boundary_scope}")
    print()

    # Step 1 — create a full-permission lab token
    lab_token, internal_id = generate_lab_token(base_url, admin_token, app_name)

    # Step 2 — create the application perspective
    print("[2/4] Creating application perspective ...")
    payload = build_payload(app_name, matching_rules, boundary_scope)
    url     = f"{base_url}/api/application-monitoring/settings/application"
    status, body = _request("POST", url, token=lab_token, payload=payload)

    print(f"[3/4] Response — HTTP {status}")

    # Step 3 — clean up lab token regardless of outcome
    delete_lab_token(base_url, admin_token, internal_id)

    # Report
    if status in (200, 201):
        app_id    = body.get("id",    "<unknown>") if isinstance(body, dict) else "<unknown>"
        app_label = body.get("label", app_name)    if isinstance(body, dict) else app_name
        print()
        print("=" * 55)
        print("  Application Perspective Created Successfully")
        print("=" * 55)
        print(f"  Name : {app_label}")
        print(f"  ID   : {app_id}")
        print()
        print(f"  Open in Instana UI:")
        print(f"    {base_url}/#/application;appId={app_id}")
        print()
        print("[Done]")
    elif status == 400:
        errors = body.get("errors") or body.get("message") or body.get("error") or json.dumps(body) if isinstance(body, dict) else str(body)
        print(f"\n[ERROR] Bad request — payload rejected.\n        Details: {errors}", file=sys.stderr)
        sys.exit(1)
    elif status == 401:
        print("\n[ERROR] Unauthorized — check INSTANA_TOKEN has 'canConfigureApplications'.", file=sys.stderr)
        sys.exit(1)
    elif status == 409:
        print(f"\n[ERROR] Conflict — '{app_name}' already exists. Choose a different APP_NAME.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n[ERROR] Unexpected response: HTTP {status}", file=sys.stderr)
        print(json.dumps(body, indent=2) if isinstance(body, dict) else body, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
