#!/usr/bin/env bash
# =============================================================================
# create_application.sh
# Creates a new Application Perspective in Instana using tag-based service
# matching rules.  All configuration is read from inputs.env.
#
# Usage:
#   1. Fill in inputs.env  (INSTANA_TOKEN, APP_NAME, APP_TAGS are required)
#   2. bash create_application.sh
#
# Flow:
#   1. Load + validate inputs.env
#   2. POST /api/settings/api-tokens  (apiToken auth) → create a full-permission
#      lab token; caller supplies accessGrantingToken + internalId as UUIDs
#   3. POST /api/application-monitoring/settings/application  (lab token)
#   4. DELETE /api/settings/api-tokens/{internalId} → clean up lab token
#   5. Print the new application ID on success
#
# Reference:
#   POST /api/application-monitoring/settings/application
#   https://developer.ibm.com/apis/catalog/instana--instana-rest-api/api/API--instana--instana-rest-api-documentation#addApplicationConfig
#
# Compatible with bash 3.2 (macOS) and bash 4+ (Linux)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Load inputs.env
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUTS_FILE="${SCRIPT_DIR}/inputs.env"

if [[ ! -f "${INPUTS_FILE}" ]]; then
  echo "[ERROR] inputs.env not found at ${INPUTS_FILE}"
  exit 1
fi

# shellcheck source=inputs.env
source "${INPUTS_FILE}"

# ---------------------------------------------------------------------------
# Validate required inputs
# ---------------------------------------------------------------------------
errors=0
if [[ -z "${INSTANA_URL:-}"     || "${INSTANA_URL}"     == *"<"* ]]; then echo "[ERROR] Set INSTANA_URL in inputs.env";     errors=1; fi
if [[ -z "${INSTANA_TOKEN:-}"   || "${INSTANA_TOKEN}"   == *"<"* ]]; then echo "[ERROR] Set INSTANA_TOKEN in inputs.env";   errors=1; fi
if [[ -z "${APP_NAME:-}"        || "${APP_NAME}"        == *"<"* ]]; then echo "[ERROR] Set APP_NAME in inputs.env";        errors=1; fi
if [[ -z "${APP_TAGS:-}"        || "${APP_TAGS}"        == *"<"* ]]; then echo "[ERROR] Set APP_TAGS in inputs.env";        errors=1; fi
[[ "${errors}" -eq 1 ]] && exit 1

BASE_URL="${INSTANA_URL%/}"
BOUNDARY_SCOPE="${BOUNDARY_SCOPE:-ALL}"

# ---------------------------------------------------------------------------
# Temp files — cleaned up on exit
# ---------------------------------------------------------------------------
TMP_PAYLOAD="/tmp/instana_app_payload_$$.json"
TMP_TOKEN="/tmp/instana_token_$$.json"
cleanup() { rm -f "${TMP_PAYLOAD}" "${TMP_TOKEN}"; }
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------
echo ""
echo "Instana host     : ${BASE_URL}"
echo "Application name : ${APP_NAME}"
echo "Boundary scope   : ${BOUNDARY_SCOPE}"
echo "Tags             : ${APP_TAGS}"
echo ""

# ---------------------------------------------------------------------------
# Step 1 — Create a full-permission lab token using apiToken auth
# ---------------------------------------------------------------------------
echo "[1/4] Generating full-permission lab token ..."

python3 - <<PYEOF > "${TMP_TOKEN}"
import json, uuid, urllib.request, urllib.error, ssl, sys

base_url    = "${BASE_URL}"
admin_token = "${INSTANA_TOKEN}"
app_name    = "${APP_NAME}"

# Caller-supplied UUIDs — required by this Instana version
access_granting_token = uuid.uuid4().hex[:22]
internal_id           = uuid.uuid4().hex[:22]

payload = {
    "name":                 "lab1b-" + app_name[:20] + "-token",
    "accessGrantingToken":  access_granting_token,
    "internalId":           internal_id,
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

req = urllib.request.Request(
    base_url + "/api/settings/api-tokens",
    data=json.dumps(payload).encode("utf-8"),
    method="POST",
    headers={
        "Authorization": "apiToken " + admin_token,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    },
)
ctx = ssl._create_unverified_context()
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        body = json.loads(r.read().decode("utf-8") or "{}")
        print(str(r.status) + "|" + json.dumps(body))
except urllib.error.HTTPError as e:
    body = json.loads(e.read().decode("utf-8", errors="replace") or "{}")
    print(str(e.code) + "|" + json.dumps(body))
except urllib.error.URLError as e:
    sys.stderr.write("[ERROR] Could not reach Instana: " + str(e.reason) + "\n")
    sys.exit(1)
PYEOF

TOKEN_RESULT="$(cat "${TMP_TOKEN}")"
TOKEN_STATUS="${TOKEN_RESULT%%|*}"
TOKEN_BODY="${TOKEN_RESULT#*|}"

if [[ "${TOKEN_STATUS}" != "200" && "${TOKEN_STATUS}" != "201" ]]; then
  MSG=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('errors') or d.get('message') or d.get('error') or str(d))" <<< "${TOKEN_BODY}" 2>/dev/null || echo "${TOKEN_BODY}")
  echo "[ERROR] Failed to create lab token — HTTP ${TOKEN_STATUS}: ${MSG}"
  exit 1
fi

# Extract the token value and internalId from the response
LAB_TOKEN=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('accessGrantingToken') or '')
" <<< "${TOKEN_BODY}")

TOKEN_INTERNAL_ID=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('internalId') or '')
" <<< "${TOKEN_BODY}")

if [[ -z "${LAB_TOKEN}" ]]; then
  echo "[ERROR] Token created but accessGrantingToken not found in response."
  echo "        Response: ${TOKEN_BODY}"
  exit 1
fi

echo "       Lab token created (internalId: ${TOKEN_INTERNAL_ID})"

# ---------------------------------------------------------------------------
# Step 2 — Build the application perspective payload
# ---------------------------------------------------------------------------
python3 - <<PYEOF > "${TMP_PAYLOAD}"
import json, sys

app_name       = """${APP_NAME}"""
raw_tags       = """${APP_TAGS}"""
boundary_scope = "${BOUNDARY_SCOPE}"

rules = []
for seg in raw_tags.split(";"):
    seg = seg.strip()
    if not seg or "=" not in seg:
        continue
    key, _, val = seg.partition("=")
    rules.append({
        "key":      key.strip(),
        "value":    val.strip(),
        "operator": "EQUALS",
        "entity":   "DESTINATION",
    })

if not rules:
    sys.stderr.write("[ERROR] APP_TAGS produced no valid rules. "
                     "Use format: key=value or key1=value1;key2=value2\n")
    sys.exit(1)

def tag_filter(rule):
    return {
        "type":        "TAG_FILTER",
        "name":        rule["key"],
        "stringValue": rule["value"],
        "value":       rule["value"],
        "operator":    rule["operator"],
        "entity":      rule["entity"],
    }

if len(rules) == 1:
    tag_filter_expression = tag_filter(rules[0])
else:
    tag_filter_expression = {
        "type":            "EXPRESSION",
        "logicalOperator": "AND",
        "elements":        [tag_filter(r) for r in rules],
    }

payload = {
    "label":               app_name,
    "scope":               "INCLUDE_ALL_DOWNSTREAM",
    "boundaryScope":       boundary_scope,
    "tagFilterExpression": tag_filter_expression,
    "accessRules": [
        {"accessType": "READ_WRITE", "relationType": "GLOBAL", "relatedId": None}
    ],
}

print(json.dumps(payload, indent=2))
PYEOF

# ---------------------------------------------------------------------------
# Step 3 — POST the application perspective using the lab token
# ---------------------------------------------------------------------------
echo "[2/4] Creating application perspective ..."

HTTP_RESULT=$(python3 - <<PYEOF
import urllib.request, urllib.error, ssl, sys, json

base_url  = "${BASE_URL}"
lab_token = "${LAB_TOKEN}"

with open("${TMP_PAYLOAD}") as f:
    payload = f.read().encode("utf-8")

req = urllib.request.Request(
    base_url + "/api/application-monitoring/settings/application",
    data=payload,
    method="POST",
    headers={
        "Authorization": "apiToken " + lab_token,
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    },
)
ctx = ssl._create_unverified_context()
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        body = r.read().decode("utf-8") or "{}"
        print(str(r.status) + "|" + body)
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace") or "{}"
    print(str(e.code) + "|" + body)
except urllib.error.URLError as e:
    sys.stderr.write("[ERROR] Could not reach Instana: " + str(e.reason) + "\n")
    sys.exit(1)
PYEOF
)

STATUS="${HTTP_RESULT%%|*}"
BODY="${HTTP_RESULT#*|}"

echo "[3/4] Response — HTTP ${STATUS}"

# ---------------------------------------------------------------------------
# Step 4 — Delete the lab token (always, regardless of outcome)
# ---------------------------------------------------------------------------
if [[ -n "${TOKEN_INTERNAL_ID}" ]]; then
  echo "[4/4] Cleaning up lab token (internalId: ${TOKEN_INTERNAL_ID}) ..."
  python3 - <<PYEOF 2>&1 || echo "[WARN] Could not delete token — delete it manually in the Instana UI."
import urllib.request, urllib.error, ssl, sys

base_url    = "${BASE_URL}"
admin_token = "${INSTANA_TOKEN}"
internal_id = "${TOKEN_INTERNAL_ID}"

req = urllib.request.Request(
    base_url + "/api/settings/api-tokens/" + internal_id,
    method="DELETE",
    headers={"Authorization": "apiToken " + admin_token, "Accept": "application/json"},
)
ctx = ssl._create_unverified_context()
try:
    with urllib.request.urlopen(req, context=ctx) as r:
        sys.stdout.write("       Token deleted.\n")
except urllib.error.HTTPError as e:
    sys.stdout.write("[WARN] Delete returned HTTP " + str(e.code) + "\n")
PYEOF
fi

# ---------------------------------------------------------------------------
# Report result
# ---------------------------------------------------------------------------
if [[ "${STATUS}" == "200" || "${STATUS}" == "201" ]]; then
  APP_ID=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('id','<unknown>'))" <<< "${BODY}")
  echo ""
  echo "======================================================="
  echo "  Application Perspective Created Successfully"
  echo "======================================================="
  echo "  Name : ${APP_NAME}"
  echo "  ID   : ${APP_ID}"
  echo ""
  echo "  Open in Instana UI:"
  echo "    ${BASE_URL}/#/application;appId=${APP_ID}"
  echo ""
  echo "[Done]"

elif [[ "${STATUS}" == "400" ]]; then
  MSG=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('errors') or d.get('message') or d.get('error') or str(d))" <<< "${BODY}" 2>/dev/null || echo "${BODY}")
  echo ""
  echo "[ERROR] Bad request — payload rejected."
  echo "        Details: ${MSG}"
  exit 1

elif [[ "${STATUS}" == "401" ]]; then
  echo ""
  echo "[ERROR] Unauthorized — check INSTANA_TOKEN has 'canConfigureApplications'."
  exit 1

elif [[ "${STATUS}" == "409" ]]; then
  echo ""
  echo "[ERROR] Conflict — '${APP_NAME}' already exists. Choose a different APP_NAME."
  exit 1

else
  echo ""
  echo "[ERROR] Unexpected response: HTTP ${STATUS}"
  echo "${BODY}" | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(json.dumps(d,indent=2))" 2>/dev/null || echo "${BODY}"
  exit 1
fi
