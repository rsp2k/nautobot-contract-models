# Service Provider

The vendor / counterparty on a contract. Service providers are independent of contracts — a provider can have many contracts (or none), and contracts can change provider over their lifetime (rare, but possible).

## Fields

| Field | Type | Notes |
|---|---|---|
| `name` | string | Display name (max 255). Natural key. Unique. |
| `account_number` | string | Vendor-side account identifier. |
| `portal_url` | URL | Self-service / billing / ticketing portal. |
| `support_email` | email | Operations support contact. |
| `support_phone` | string | Operations support phone. |
| `description` | string | Short description (max 200). |
| `comments` | text | Long-form notes. |

## Natural key

`name` — set via `unique=True` on the field.

## Related models

- `Contract` (FK from Contract, PROTECT) — can't delete a provider with active contracts.

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `webhooks`, plus auto-wired Notes / Changelog / Contacts / Data Compliance.
