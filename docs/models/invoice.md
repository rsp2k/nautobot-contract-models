# Invoice

One billing line on a contract. Invoices belong to exactly one contract and are deleted with it (CASCADE).

## Fields

| Field | Type | Notes |
|---|---|---|
| `contract` | FK Contract | Parent contract. CASCADE on delete. |
| `invoice_number` | string | Vendor-supplied invoice number (max 100). |
| `invoice_date` | date | Date the invoice was issued. |
| `due_date` | date | When payment is due. Nullable. |
| `paid_date` | date | When the invoice was paid. Nullable. |
| `is_paid` | bool | Convenience flag. |
| `total_amount` | Decimal(12,2) | Total invoiced amount. |
| `currency` | char(3) | ISO 4217. Inherits from contract by convention but stored explicitly. |
| `status` | StatusField | Active / Expired / Cancelled / Pending. |
| `description` | string | Short description (max 200). |
| `comments` | text | Long-form notes. |

## Natural key

`(contract, invoice_number)`.

## Related models

- `InvoiceAttachment` — file uploads (PDF copies of the invoice itself, supporting docs).

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `statuses`, `webhooks`, plus auto-wired Notes / Changelog / Contacts / Data Compliance.
