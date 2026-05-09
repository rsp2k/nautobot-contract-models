# Cost Snapshot

A point-in-time aggregate of fleet contract costs. One row per (date, currency). Snapshots are write-once telemetry — there's no "edit a snapshot" workflow, and we never delete a snapshot when a contract changes.

## Fields

| Field | Type | Notes |
|---|---|---|
| `snapshot_date` | date | The date this snapshot represents. |
| `currency` | char(3) | ISO 4217. Multiple currencies on the same date = multiple rows. |
| `monthly_burn` | Decimal(14,2) | Sum of `monthly_cost` across active contracts in this currency. |
| `renewal_90d` | Decimal(14,2) | Total renewal cost in the 90-day forward window from `snapshot_date`. |
| `active_contract_count` | int | Number of active contracts in this currency on the snapshot date. |
| `coverage_gap_count` | int (nullable) | Devices with no direct contract assignment. Stored on the alphabetically-first per-date snapshot only — null on others — since gap count is currency-agnostic. |

## Natural key

`(snapshot_date, currency)` — set via `natural_key_field_names`.

## Constraints

- `UniqueConstraint(snapshot_date, currency)` — prevents accidental duplicate snapshots on the same day.

## Indexes

- `(-snapshot_date, currency)` — speeds up the time-series queries the Cost History page runs.

## Why no FK to Contract?

A snapshot is a fleet aggregate, not a per-contract row. Linking to live contracts would mean deleting a contract destroys the historical record of its spend — exactly wrong, since "we used to spend $X with that vendor" is the value proposition. Snapshots are immutable historical facts, decoupled from current Contract state.

## Why subclass `BaseModel` rather than `PrimaryModel`?

Snapshots don't need ChangeLog / Tags / Relationships / dynamic groups. Operators don't tag a snapshot or relate it to a Device. `BaseModel` gives the UUID PK + natural-key machinery, which is the minimum useful surface.

## Read-only API

The `/api/plugins/contracts/cost-snapshots/` endpoint exposes list + retrieve only — POST / PATCH / DELETE return `405 Method Not Allowed`. The viewset composes DRF's `ListModelMixin + RetrieveModelMixin + GenericViewSet` directly, so write methods aren't even routable. See [External Interactions — REST API](../user/external_interactions.md#rest-api).

## Captured by

The `Capture cost history snapshot` Job (run weekly). The Job calls `cost.take_snapshot()` which `update_or_create`s one row per (date, currency).

## Extras features enabled

`graphql`. (No `webhooks` — snapshots are telemetry, not user-managed; no `custom_fields` — operator-tagged metadata doesn't fit the immutable-record model.)
