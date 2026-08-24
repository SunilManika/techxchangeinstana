# add_instana_user

Bulk-invite users to a self-hosted or SaaS Instana instance from a CSV file using the Instana REST API.

---

## Files

| File | Description |
|---|---|
| `add_instana_user.py` | Main script |
| `users.csv` | Input CSV — one user per row |
| `.env.example` | Template for credentials — copy to `.env` and fill in |

---

## Prerequisites

- Python 3.9+
- `requests` library

```bash
pip install requests
```

---

## Setup

### 1. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
INSTANA_BASE_URL=https://unit0-techzone.150-240-162-27.nip.io
INSTANA_API_TOKEN=your-api-token-here
```

> The API token must have **"Configuration of users"** (`canConfigureUsers`) permission.  
> Go to **Settings → Access Control → API Tokens** in the Instana UI to create one.

### 2. Prepare the CSV

Edit `users.csv` — one user per row:

```csv
email,fullName,role,groupId
jane.doe@example.com,Jane Doe,USER,-1
john.smith@example.com,John Smith,ADMIN,-1
```

| Column | Required | Values | Default |
|---|---|---|---|
| `email` | ✅ | Any valid email | — |
| `fullName` | ✅ | Display name | — |
| `role` | ❌ | `ADMIN`, `USER`, `VIEWER` | `USER` |
| `groupId` | ❌ | RBAC group ID, or `-1` for none | `-1` |

---

## Usage

### Linux / macOS

```bash
source .env
python add_instana_user.py users.csv
```

### Windows PowerShell

```powershell
Get-Content .env | ForEach-Object { $k,$v = $_ -split '=',2; Set-Item "env:$k" $v }
python add_instana_user.py users.csv
```

Or set variables inline:

```powershell
$env:INSTANA_BASE_URL  = "https://unit0-techzone.150-240-162-27.nip.io"
$env:INSTANA_API_TOKEN = "your-api-token-here"
python add_instana_user.py users.csv
```

---

## Optional flags

| Flag | Description |
|---|---|
| `--dry-run` | Print what would be sent without calling the API |
| `--log FILE` | Write detailed JSON results to `FILE` (default: `invite_log.json`) |
| `--no-log` | Disable log file output entirely |

### Dry run example

```bash
python add_instana_user.py users.csv --dry-run
```

---

## Output

```
Inviting 2 user(s)...

  [OK] Invited: Jane Doe <jane.doe@example.com> role=USER groupId=-1
  [OK] Invited: John Smith <john.smith@example.com> role=ADMIN groupId=-1

Done. 2 succeeded, 0 failed.

Log saved to: invite_log.json
```

### Invite statuses

| `invitationStatus` | Meaning |
|---|---|
| `SUCCESS` | Invitation email sent successfully |
| `INTERNAL_ERROR` | Instana could not send the email — usually SMTP not configured |

---

## Troubleshooting

### `INTERNAL_ERROR` on invite

The Instana instance has no SMTP configured. SSH into the server and add an `email` block to `/opt/instana/settings.hcl`:

```hcl
email {
  smtp {
    from      = "instana-noreply@yourdomain.com"
    host      = "your-smtp-host.com"
    port      = 587
    use_ssl   = false
    start_tls = true
    use_auth  = true
    user      = "your-smtp-username"
    password  = "your-smtp-password"
  }
}
```

Then apply and restart:

```bash
instana update -f /opt/instana/settings.hcl
instana restart backend
```

### SSL certificate error

Self-hosted TechZone instances use self-signed certificates. The script already handles this with `verify=False`. The `InsecureRequestWarning` in stderr is expected and safe to ignore in lab environments.

### `403 Forbidden`

The API token does not have `canConfigureUsers` permission. Regenerate the token with that permission enabled.

---

## .gitignore recommendations

Add the following to your `.gitignore` to avoid committing secrets or PII:

```
.env
*_log.json
invite_log.json
test_*.csv
__pycache__/
*.py[cod]
.venv/
```

---

## License

MIT
