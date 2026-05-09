# Contract

The master vendor agreement, with dates, costs, status, and a structured SLA shape. Every contract belongs to a `ServiceProvider` and may be scoped to a `Tenant`.

## Fields

### Core

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name (max 255). Part of the natural key. |
| `contract_number` | string | Vendor-supplied number; not unique. |
| `provider` | FK ServiceProvider | PROTECT — can't delete a provider with active contracts. |
| `tenant` | FK Tenant | Nullable. SET_NULL on tenant delete. |
| `status` | StatusField | Active / Expired / Cancelled / Pending (registered at install). |
| `start_date` | date | When coverage starts. |
| `end_date` | date | When coverage ends; drives the renewal calendar and Action Required priority. |

### Cost

| Field | Type | Notes |
|---|---|---|
| `recurring_cost` | Decimal(12,2) | Periodic cost in `currency`. Combined with `billing_period` for normalization. |
| `billing_period` | choice | `monthly` / `quarterly` / `semiannual` / `annual` / `one_time`. Drives burn-rate normalization. |
| `one_time_cost` | Decimal(12,2) | Setup / activation / migration fees. Excluded from burn rate; included in `total_contract_value`. |
| `currency` | char(3) | ISO 4217 (USD, EUR, GBP). Aggregations group by this; never sum across. |

### SLA / contract shape

| Field | Type | Notes |
|---|---|---|
| `contract_type` | choice | `hardware` / `software` / `saas` / `services` / `managed` / `support` / `warranty` / `other` |
| `coverage_hours` | choice | `24x7` / `24x5` / `business_hours` / `8x5_nbd` / `best_effort` |
| `response_time` | choice | `1h` / `2h` / `4h` / `8h` / `nbd` / `best_effort` |
| `restoration_time` | choice | `4h` / `8h` / `24h` / `nbd` / `2d` / `5d` / `none` |
| `notice_period_days` | int | Days before `end_date` by which a cancellation notice must be served. Used by the priority rubric to escalate. |
| `auto_renew` | bool | If true, contract auto-renews unless action is taken — flips priority to URGENT inside the notice window. |
| `term_months` | int | Original term length. Drives `total_contract_value` calculations. Null = perpetual / month-to-month. |

### Free-form

| Field | Type | Notes |
|---|---|---|
| `renewal_terms` | string | Free-form, e.g. "Auto-renew unless cancelled 60d prior". |
| `description` | string | Short description (max 200). |
| `comments` | text | Long-form notes. (See also the auto-wired Notes tab on the detail page.) |

## Natural key

`(provider, name)` — set via `natural_key_field_names = ["name", "provider"]` (a Nautobot-level attribute, NOT a Django Meta attribute). Neither field is unique on its own — yearly renewals reuse names; numbers can collide across providers — so the pair is the natural key.

## Constraints

- `CheckConstraint(end_date__gte=start_date)` — names "nbcm_contract_end_after_start"

## Computed properties

- `is_expired` — True if `end_date` is in the past
- `is_expiring_within(days)` — True if `end_date` falls within `days` from today

## Related models

- `Invoice` (FK to Contract, CASCADE delete) — billing lines
- `ContractAssignment` (FK to Contract, CASCADE) — generic-FK link to any Nautobot object
- `ContractAttachment` (FK to Contract, CASCADE) — file uploads (signed PDFs, etc.)

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `statuses`, `webhooks`, plus auto-wired Notes / Changelog / Contacts / Data Compliance via the UI viewset router.
