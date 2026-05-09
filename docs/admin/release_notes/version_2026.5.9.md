# v2026.5.9

Released **2026-05-09**. First public release.

This release covers a sixteen-phase build that took the plugin from "scaffold" to "shipped" in about 24 hours of focused work. Every phase shipped end-to-end with tests, browser verification, and updated docs.

## Schema

- 8 migrations (`0001` → `0008`)
- 7 models: `ServiceProvider`, `Contract`, `Invoice`, `ContractAssignment`, `ContractAttachment`, `InvoiceAttachment`, `CostSnapshot`
- 4 ChoiceSet enums: `ContractTypeChoices`, `CoverageHoursChoices`, `ResponseTimeChoices`, `RestorationTimeChoices`, `BillingPeriodChoices`

## What's in this release

### Core data model

- `ServiceProvider`, `Contract`, `Invoice`, `ContractAssignment` — the v1 spine
- Generic-FK `ContractAssignment` so one contract row can cover any Nautobot model with a UUID PK
- 4 statuses (Active / Expired / Cancelled / Pending) registered at install via data migration

### Real-world contract structure (Phase 7)

- Structured SLA fields on `Contract`: `contract_type`, `coverage_hours`, `response_time`, `restoration_time`, `notice_period_days`, `auto_renew`, `term_months`
- Per-assignment scope on `ContractAssignment`: `coverage_start`, `coverage_end`, `scope_notes`, `is_primary`
- Transitive coverage helper walking `(self, tenant, location, rack, device)` ancestry
- `CoverageGapJob` + "Coverage Gaps" home dashboard panel

### Cost analytics (Phase 8)

- `Contract.billing_period` ChoiceSet (monthly/quarterly/semiannual/annual/one_time)
- `cost.py` with 7 helpers (per-contract math + fleet-wide aggregations)
- "Cost Summary" + "Renewal Forecast" home dashboard panels (per-currency, no FX conversion)
- `CostReportJob` writes burn / renewal / top vendor / gap-count to JobLogEntry

### Renewal Calendar (Phase 9 + 10)

- Forward-looking month-by-month grid at `/reports/renewal-calendar/`
- Single-hue amber saturation scale, dark-mode-aware, print-friendly
- "NOW" badge + amber rails on the current month
- Hover tooltips with per-cell contract names
- Cross-link from the Renewal Forecast dashboard panel

### Bulk CSV import (Phase 11)

- Standard Nautobot import flow at `/contracts/import/` — fully auto-wired by `NautobotUIViewSetRouter`
- Sample CSV + format quirks docs in `development/sample-data/`

### Action Required surface (Phase 12)

- Centralized `priority.action_priority()` rubric — URGENT / WARNING / INFO
- `RenewalCheckJob` refactored to use the same rubric (log lines tagged `[URGENT]` / `[WARNING]` / `[INFO]`)
- Dedicated page at `/reports/action-required/` with three bucket cards
- "Action Required" home dashboard panel showing top 5 priority items

### Cost history time-series (Phase 13)

- `CostSnapshot` model — write-once telemetry decoupled from Contract live state
- `cost.take_snapshot()` + `cost.history()` helpers
- `CostHistoryJob` for weekly persistence
- `/reports/cost-history/` page with three inline-SVG line charts (no JS chart library)

### REST API for snapshots (Phase 14)

- Read-only endpoint at `/api/plugins/contracts/cost-snapshots/`
- DRF mixin composition (`ListModelMixin + RetrieveModelMixin + GenericViewSet`) — write methods aren't routable, returns 405
- Filterable by `snapshot_date__gte`, `snapshot_date__lte`, `currency`

### Cost-anomaly detection (Phase 15)

- `cost.detect_anomalies(threshold, lookback_weeks)` helper
- `CostAnomalyJob` with configurable thresholds
- New currencies report `pct_change=None` so callers can render "NEW"

### Notes (Phase 16)

- Auto-wired by Nautobot's `NautobotUIViewSetRouter` — no plugin code needed
- Markdown notes on every Contract / Invoice / ServiceProvider / Assignment / Attachment

## Tests

73 integration tests + 9 anomaly tests = **82 tests, all passing.** Coverage spans:

- Transitive coverage walking
- Severity rubric edge cases
- billing_period normalization
- Per-currency aggregation
- Cost-history snapshot idempotency
- Anomaly threshold logic
- Calendar window math

## Breaking changes

None — first release.

## Known issues

- Migration `0007_contract_billing_period` defaults existing contracts to `billing_period='monthly'`. If you're somehow upgrading from a development copy that pre-dates Phase 8, edit annual/quarterly contracts after migration to fix the burn-rate calculation. (Not applicable to fresh installs.)

## Upgrade path

This is the first release; install fresh per [Install](../install.md).
