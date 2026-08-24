# Lab1b — Create an Instana Application Perspective

This lab creates a new **Application Perspective** in Instana via the REST API.  
An Application Perspective groups services by tag-based matching rules and gives you a dedicated observability view — topology, calls, errors, and latency — scoped to exactly the services you care about.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.8+ | Standard library only — no `pip install` needed |
| Instana API token | Must have **"Configuration of applications"** permission |
| Network access | Script skips TLS verification for self-signed certificates |

---

## Quick start

```bash
# 1. Edit inputs.env
vi Lab1b/inputs.env

# 2. Run (choose one)
python3 Lab1b/create_application.py
# or
bash Lab1b/create_application.sh
```

---

## Configuration (`inputs.env`)

| Variable | Required | Description |
|---|---|---|
| `INSTANA_URL` | ✅ | Base URL of your Instana tenant, no trailing slash |
| `INSTANA_TOKEN` | ✅ | API token with "Configuration of applications" permission |
| `APP_NAME` | ✅ | Display name for the new application perspective |
| `APP_TAGS` | ✅ | Semicolon-separated `key=value` tag rules (see below) |
| `DOWNSTREAM_SCOPE` | optional | `ALL` (default) — include all downstream services |
| `BOUNDARY_SCOPE` | optional | `ALL` (default) — include all calls |

### `APP_TAGS` format

Each `key=value` pair defines one tag-match rule.  
Multiple pairs are combined with **AND** logic — a call must match all rules to be included.

```
# Single tag
APP_TAGS="service.name=checkout"

# Multiple tags (AND)
APP_TAGS="kubernetes.namespace.name=production;service.name=frontend"
```

Common tag keys used in Instana:

| Tag key | Example value |
|---|---|
| `service.name` | `checkout` |
| `kubernetes.namespace.name` | `production` |
| `kubernetes.cluster.name` | `my-cluster` |
| `agent.tag` | `env:prod` |

---

## What the script does

```
1. Load + validate inputs.env
2. Parse APP_TAGS → build matchExpression JSON
       Single tag  → LEAF node
       Multi  tags → EXPRESSION node with AND logic
3. POST /api/application-monitoring/settings/application
4. Print the new application ID + a direct UI link on success
```

### API payload example

```json
{
  "label": "My Application",
  "scope": "ALL",
  "boundaryScope": "ALL",
  "matchExpression": {
    "type": "LEAF",
    "key": "service.name",
    "value": "checkout",
    "operator": "EQUALS",
    "entity": "DESTINATION"
  },
  "accessRules": []
}
```

---

## Expected output

```
Instana host     : https://instana.example.com
Application name : My Application
Downstream scope : ALL
Boundary scope   : ALL
Tags             : service.name=checkout

[1/2] Creating application perspective ...
[2/2] Response — HTTP 201

=======================================================
  Application Perspective Created Successfully
=======================================================
  Name : My Application
  ID   : a1b2c3d4e5f6

  Open in Instana UI:
    https://instana.example.com/#/application;appId=a1b2c3d4e5f6

[Done]
```

---

## API reference

`POST /api/application-monitoring/settings/application`  
[IBM Developer — Instana REST API: addApplicationConfig](https://developer.ibm.com/apis/catalog/instana--instana-rest-api/api/API--instana--instana-rest-api-documentation#addApplicationConfig)
