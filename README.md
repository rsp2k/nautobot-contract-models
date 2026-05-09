# nautobot-contract-models

A Nautobot content plugin that adds first-class models for **vendor contracts**, **invoices**, **renewal tracking**, and **PDF attachments**, with the relationships needed to answer questions like:

- *Which contracts expire in the next 60 days?*
- *Which devices are covered by an active support contract, and which aren't?*
- *What did we pay last quarter for circuit X, and is it trending up?*
- *Show me the signed PDF of the master services agreement we have with Acme.*

Inspired by [netbox-contract](https://github.com/mlebreuil/netbox-contract), but re-architected for Nautobot 3.x conventions: `PrimaryModel`, the Status framework, `Tenant`, ChangeLog, the Job framework, and the modern `NautobotUIViewSet` / `ObjectDetailContent` UI Component Framework.

## Status

Tested against **Nautobot 3.1.1**. CalVer versioning (`YYYY.M.D`) — see `pyproject.toml` for the version that was current when you cloned.

## Models

| Model | Role | Lifecycle |
|---|---|---|
| `ServiceProvider` | The vendor / counterparty | Independent — referenced by Contracts |
| `Contract` | The master agreement: dates, costs, currency, status | Owned by a ServiceProvider (PROTECT); optional Tenant (SET_NULL) |
| `Invoice` | One billing line on a Contract | CASCADE on Contract delete |
| `ContractAssignment` | Generic-FK link between a Contract and any Nautobot object (Device, Circuit, VirtualMachine, …) | CASCADE on Contract delete; PROTECT on target ContentType |
| `InvoiceAttachment` | A file uploaded against an Invoice (typically the vendor PDF) | CASCADE on Invoice delete |
| `ContractAttachment` | A file uploaded against a Contract (signed PDF, SOW, renewal letter) | CASCADE on Contract delete |

All six are `PrimaryModel` subclasses, so they get for free: ChangeLog, custom fields, tags, dynamic groups, REST API, GraphQL, webhooks, notes, contacts, computed fields.

The `ContractAssignment` model uses Django's `ContentType` + `GenericForeignKey` so one model handles all target types — no separate `ContractDevice`, `ContractCircuit`, `ContractVM` tables. Operators can attach a Contract to anything in the Nautobot ORM with a UUID PK.

## Install

```bash
pip install nautobot-contract-models
```

Add to `nautobot_config.py`:

```python
PLUGINS = ["nautobot_contract_models"]

PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        # Days-out window for the renewal-alert Job + home-dashboard panel.
        # Default: 60. Override via env var, file, etc. as you would any
        # PLUGINS_CONFIG entry.
        "renewal_window_days": 60,
    },
}
```

Then run migrations:

```bash
nautobot-server migrate nautobot_contract_models
```

The `0002_register_statuses` data migration creates four `Status` records (Active, Expired, Cancelled, Pending) and binds them to the Contract and Invoice content types. Idempotent — safe to re-run.

### After install

The renewal-check Job ships **disabled** (Nautobot 3.x default for newly-discovered Jobs). To enable it:

1. **Apps → Jobs**, find "Check upcoming renewals" under the *Contracts* group
2. Edit the Job, check **Enabled**, save
3. (Optional) Configure a recurring schedule: **Apps → Jobs → Scheduled Jobs → Add**

## Configuration via PLUGINS_CONFIG

| Key | Type | Default | Effect |
|---|---|---|---|
| `renewal_window_days` | int | `60` | Window in days for the renewal-alert Job's default + the homepage "Upcoming Renewals" panel |

## REST API

The plugin exposes a full REST API under `/api/plugins/contracts/`. Authentication is the standard Nautobot token; pass via `Authorization: Token <key>` header.

```bash
TOKEN=...
BASE=https://nautobot.example.com/api/plugins/contracts

# List contracts, with count fields populated
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/"

# Same query but with FKs expanded inline (provider, status, tenant)
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/?depth=1"

# Filter by name + currency
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/?currency=USD&name__ic=acme"

# Find contracts expiring before a date
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/?end_date__lte=2026-12-31"

# Create a Contract
curl -H "Authorization: Token $TOKEN" -X POST "$BASE/contracts/" \
  -d '{"name":"Acme MSA","provider":"<provider-uuid>","status":"<active-status-uuid>",
       "start_date":"2026-01-01","end_date":"2027-01-01","recurring_cost":"1200.00"}' \
  -H "Content-Type: application/json"
```

Six endpoints, all with the standard list/detail/create/edit/delete + filter + bulk actions:

| Path | Model |
|---|---|
| `/api/plugins/contracts/service-providers/` | ServiceProvider |
| `/api/plugins/contracts/contracts/` | Contract |
| `/api/plugins/contracts/invoices/` | Invoice |
| `/api/plugins/contracts/contract-assignments/` | ContractAssignment |
| `/api/plugins/contracts/contract-attachments/` | ContractAttachment |
| `/api/plugins/contracts/invoice-attachments/` | InvoiceAttachment |

Count annotations included in responses: `contract_count` (on ServiceProvider); `invoice_count`, `assignment_count`, `attachment_count` (on Contract); `attachment_count` (on Invoice).

## GraphQL

All six models register in Nautobot's GraphQL schema automatically. Single-call cross-table queries:

```graphql
{
  contracts {
    name
    end_date
    recurring_cost
    currency
    provider { name account_number }
    status { name }
  }
  service_providers {
    name
    contracts { name end_date }
  }
}
```

POST to `/api/graphql/` with `Authorization: Token <key>` and `Content-Type: application/json`. The interactive GraphiQL explorer is at `/graphql/`.

## The renewal-check Job

`Check upcoming renewals` (under the *Contracts* group):

- Walks active contracts, finds rows whose `end_date` falls within `window_days` (default from `PLUGINS_CONFIG.renewal_window_days`)
- Logs a per-contract entry — `WARNING` level for contracts expiring within 7 days, `INFO` otherwise
- Returns the count, surfaced in the JobResult UI's "Result" field
- Read-only: doesn't modify contracts

```bash
# Run via CLI
nautobot-server runjob "Contracts.RenewalCheckJob"

# Or via the API
curl -H "Authorization: Token $TOKEN" -X POST \
  "https://nautobot.example.com/api/extras/jobs/<job-uuid>/run/" \
  -d '{"data": {"window_days": 30, "include_expired": false}}' \
  -H "Content-Type: application/json"
```

Each per-contract log entry has the Contract attached as the JobLogEntry's `object`, so it shows up as a clickable link in the result UI. To route warnings into Slack/email/PagerDuty, configure a webhook on JobLogEntry creation in **Apps → Webhooks**.

## Home dashboard panel

A "Contracts" panel appears on Nautobot's home page showing the next 10 contracts within `renewal_window_days`, ordered soonest first. Each row links to the contract detail page. The panel respects the user's `view_contract` permission and renders an empty-state message when there are no upcoming renewals.

## File attachments

Both `Contract` and `Invoice` support multiple file attachments (the upload field accepts any file type — typically PDF for invoices and signed contracts).

Files are stored under Nautobot's `MEDIA_ROOT`:

- `invoice_attachments/YYYY/MM/<filename>`
- `contract_attachments/YYYY/MM/<filename>`

Served at `/media/invoice_attachments/...` and `/media/contract_attachments/...`. The `nautobot-media` Docker volume persists files across container restarts.

⚠️ **Production-deploy note:** files are NOT included in DB dumps. Production deployments need a separate backup strategy for `MEDIA_ROOT` (or configure `DEFAULT_FILE_STORAGE` for S3/cloud storage and back that up via cloud-provider tooling).

## UI walkthrough

After install, the Nautobot left sidebar gains a "Contracts" tab with four list views: Contracts, Invoices, Service Providers, Assignments. Each list view supports the standard Nautobot conventions:

- Filtering, sorting, column toggling
- Bulk edit / bulk delete
- CSV import / export
- Saved views (per-user filter sets)

Each detail page renders the model's fields, plus per-parent panels for child collections:

- **Contract** detail → Invoices, Coverage (assignments), Attachments
- **Invoice** detail → Attachments
- **ServiceProvider** detail → Contracts

Each child panel has an "Add &lt;child&gt;" button that pre-populates the parent FK, so creating an invoice from a contract's detail page lands on the create form with the contract already selected.

## Limitations

Honest about what v1 doesn't do:

- **Single currency per contract / invoice.** Costs are stored as `Decimal(12, 2)` plus a `currency` ISO 4217 CharField. No FX conversion. Reports across mixed-currency contracts are the operator's problem.
- **No approval workflows for contract changes.** Nautobot's general `ApprovalQueue` covers this case if you need it.
- **No external-system sync.** Contract data lives in Nautobot's own DB. If you need to read contracts from Hudu / ConnectWise / Lansweeper, build a separate SSoT plugin that syncs into these models.
- **No per-line-item invoice breakdown.** One `Invoice` row = one billing period. Use Nautobot custom fields or notes if you need finer granularity.
- **No multi-currency rate-tracking.** Reporting contract value in a base currency means doing the math at query time.
- **File attachments are model-specific** — `InvoiceAttachment` and `ContractAttachment` are sibling models, not a generic GFK. Adding a third attachment type means duplicating the pattern (or refactoring to a GFK model). v1 follows netbox-contract's convention of separate models per parent.
- **Production media-volume backups are out of scope.** See note above.

## Development

```bash
cd development/
cp .env.example .env
$EDITOR .env
make build && make up
```

See `development/README.md` for the full bringup walkthrough, including the four known gotchas (`COMPOSE_PROJECT_NAME` collision, volume-permission first-boot fix, worker restarts after editing jobs.py, etc.).

## License

TBD with the operator.

## Acknowledgements

- Data model inspired by [netbox-contract](https://github.com/mlebreuil/netbox-contract) by Marc Lebreuil
- Tooling and dev-stack patterns mirror the operator's [nautobot-plugin-ssot-hudu](https://github.com/rsp/nautobot-plugin-ssot-hudu)
- Built on Nautobot's [App development conventions](https://docs.nautobot.com/projects/core/en/stable/development/apps/)
