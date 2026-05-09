# Contract Attachment

A file upload attached to a `Contract`. Typical use: signed PDF master agreement, vendor escalation matrix doc, statement-of-work attachments.

## Fields

| Field | Type | Notes |
|---|---|---|
| `contract` | FK Contract | Parent contract. CASCADE on delete. |
| `file` | FileField | Uploaded file. Stored under `MEDIA_ROOT/contract_attachments/YYYY/MM/<filename>`. |
| `filename` | string | Display filename, derived from the upload. |
| `description` | string | Short description (max 200). |
| `size_bytes` | int | File size in bytes, computed at upload. |

## Storage

Files live under `MEDIA_ROOT/contract_attachments/YYYY/MM/`. The `nautobot-media` Docker volume persists them across container restarts.

⚠️ **Production-deploy note:** files are NOT included in DB dumps. Production deployments need a separate backup strategy for `MEDIA_ROOT` (or configure `DEFAULT_FILE_STORAGE` for S3 / cloud storage and back that up via cloud-provider tooling).

## Why a separate model from a generic GFK?

Mirrors the netbox-contract convention: per-parent attachment models (`ContractAttachment`, `InvoiceAttachment`) rather than a generic `Attachment(target=GFK)`. Tradeoff: adding a third attachment type means duplicating the pattern (or refactoring to a GFK model). v1 keeps it simple.

## Extras features enabled

`custom_fields`, `custom_links`, `custom_validators`, `export_templates`, `graphql`, `relationships`, `webhooks`.
