# Invoice Attachment

A file upload attached to an `Invoice`. Typical use: PDF copy of the invoice itself, supporting docs (quotes, POs, payment confirmations).

## Fields

| Field | Type | Notes |
|---|---|---|
| `invoice` | FK Invoice | Parent invoice. CASCADE on delete. |
| `file` | FileField | Uploaded file. Stored under `MEDIA_ROOT/invoice_attachments/YYYY/MM/<filename>`. |
| `filename` | string | Display filename, derived from the upload. |
| `description` | string | Short description (max 200). |
| `size_bytes` | int | File size in bytes, computed at upload. |

## Storage

Files live under `MEDIA_ROOT/invoice_attachments/YYYY/MM/`. Same backup concerns as ContractAttachment — see [Contract Attachment — Storage](contractattachment.md#storage).

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `webhooks`.
