# External Interactions

This page documents how the app exposes its data to external tooling and how external tooling can interact with it.

## REST API

All models in this app are exposed via Nautobot's standard REST API at `/api/plugins/contracts/`. Most are full CRUD; one (`CostSnapshot`) is read-only.

### Endpoints

| Endpoint | Methods | Notes |
|---|---|---|
| `/api/plugins/contracts/service-providers/` | full CRUD | |
| `/api/plugins/contracts/contracts/` | full CRUD | |
| `/api/plugins/contracts/invoices/` | full CRUD | |
| `/api/plugins/contracts/contract-assignments/` | full CRUD | |
| `/api/plugins/contracts/contract-attachments/` | full CRUD | multipart for file upload |
| `/api/plugins/contracts/invoice-attachments/` | full CRUD | multipart for file upload |
| `/api/plugins/contracts/cost-snapshots/` | **list + retrieve only** | POST/PATCH/DELETE return `405 Method Not Allowed` |

`CostSnapshot` is read-only by design: snapshots are write-once historical telemetry, captured exclusively by the `Capture cost history snapshot` Job. Allowing external writes would let tooling rewrite history, defeating the "we used to spend $X with that vendor" use case.

### Authentication

Token authentication via the standard Nautobot user-token mechanism. Generate a token under your user profile, then pass it as `Authorization: Token <token>` header.

### Example queries

```bash
TOKEN=your-token-here
BASE=https://nautobot.example.com/api/plugins/contracts

# List contracts expiring in May 2026
curl -ks -H "Authorization: Token $TOKEN" \
  "$BASE/contracts/?end_date__year=2026&end_date__month=5"

# Pull cost snapshots for the last month, USD only
curl -ks -H "Authorization: Token $TOKEN" \
  "$BASE/cost-snapshots/?currency=USD&snapshot_date__gte=2026-04-09"

# Verify CostSnapshot writes are denied
curl -ks -X POST -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"snapshot_date":"2026-01-01","currency":"USD"}' \
  "$BASE/cost-snapshots/"
# → HTTP 405 Method Not Allowed
```

### FK lookups by natural key

The standard Nautobot pattern works: `?provider=Acme%20Networks` resolves the ServiceProvider by its natural key (name). For composite natural keys, use double-underscore syntax: `?location__name=HQ`.

## GraphQL

All models with `@extras_features("graphql")` (every model in this app) are queryable through Nautobot's GraphQL endpoint at `/graphql/`. The schema is auto-generated from the model + serializer.

```graphql
{
  contracts(end_date__lte: "2026-12-31") {
    name
    provider { name }
    end_date
    recurring_cost
    billing_period
    currency
    auto_renew
  }

  cost_snapshots(currency: "USD") {
    snapshot_date
    monthly_burn
    renewal_90d
    active_contract_count
  }
}
```

## Bulk CSV Import

Migrating from a spreadsheet? Use the standard Nautobot import flow at **Contracts → Contracts → Import** (or `/plugins/contracts/contracts/import/`). The page auto-generates a field-reference table from the model + serializer — required vs optional, format hints, FK-by-name lookup syntax.

A working sample lives at `development/sample-data/contracts.csv`. Format quirks (FK by name, boolean literals as `true`/`false`, date format `YYYY-MM-DD`, `billing_period` choices) are documented in `development/sample-data/README.md`.

## Webhooks

All models in this app have `@extras_features("webhooks")`, so create / update / delete events can fan out to any HTTP endpoint via Nautobot's standard webhook configuration. Common patterns:

- POST renewal warnings into Slack on Contract update
- Notify an ITSM system when a ContractAssignment is created
- Send a finance team email when a CostSnapshot lands above an anomaly threshold (use the `JobLogEntry` webhook trigger on `Detect cost anomalies` runs)

## Job Schedulers

Five Jobs are registered under the *Contracts* group:

- `Check upcoming renewals` — read-only renewal alerts
- `Find devices without contract coverage` — read-only coverage scan
- `Monthly cost report` — read-only burn / forecast / top vendor / gap-count summary
- `Capture cost history snapshot` — writes a CostSnapshot row per currency
- `Detect cost anomalies` — reads snapshots, alerts on jumps

All five are idempotent and side-effect-free *except* `Capture cost history snapshot`, which writes one row per (date, currency). Re-running the same day is still safe — the unique constraint plus `update_or_create` prevents duplicates.

Schedule them via **Jobs → Scheduled Jobs → Add**.

## File Attachments

`Contract` and `Invoice` support file attachments stored under `MEDIA_ROOT/contract_attachments/YYYY/MM/<filename>` and `invoice_attachments/YYYY/MM/<filename>` respectively. The `nautobot-media` Docker volume persists files across container restarts.

⚠️ **Production note:** files are NOT included in DB dumps. Production deployments need a separate backup strategy for `MEDIA_ROOT`, or configure `DEFAULT_FILE_STORAGE` for S3 / cloud storage and back that up via cloud-provider tooling.
