# REST API reference

All endpoints under `/api/plugins/contracts/`. Authentication: Nautobot Token (`Authorization: Token <key>`). Content negotiation: `Accept: application/json`.

## Endpoints

| Path | Methods | Model |
|---|---|---|
| `/api/plugins/contracts/service-providers/` | GET, POST | ServiceProvider |
| `/api/plugins/contracts/service-providers/<pk>/` | GET, PUT, PATCH, DELETE | ServiceProvider |
| `/api/plugins/contracts/contracts/` | GET, POST | Contract |
| `/api/plugins/contracts/contracts/<pk>/` | GET, PUT, PATCH, DELETE | Contract |
| `/api/plugins/contracts/invoices/` | GET, POST | Invoice |
| `/api/plugins/contracts/invoices/<pk>/` | GET, PUT, PATCH, DELETE | Invoice |
| `/api/plugins/contracts/contract-assignments/` | GET, POST | ContractAssignment |
| `/api/plugins/contracts/contract-assignments/<pk>/` | GET, PUT, PATCH, DELETE | ContractAssignment |
| `/api/plugins/contracts/contract-attachments/` | GET, POST | ContractAttachment |
| `/api/plugins/contracts/contract-attachments/<pk>/` | GET, PUT, PATCH, DELETE | ContractAttachment |
| `/api/plugins/contracts/invoice-attachments/` | GET, POST | InvoiceAttachment |
| `/api/plugins/contracts/invoice-attachments/<pk>/` | GET, PUT, PATCH, DELETE | InvoiceAttachment |

Each list endpoint also exposes `/changelog/`, `/notes/`, and `/data-compliance/` sub-endpoints per record (Nautobot framework standard).

## Common patterns

### List with count fields

```bash
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/" | jq '.results[] | {name, end_date, invoice_count, attachment_count}'
```

```json
{
  "name": "Acme Master Services Agreement",
  "end_date": "2026-05-30",
  "invoice_count": 1,
  "attachment_count": 1
}
```

### Nested-FK expansion

Default response contains lightweight FK references (`{id, object_type, url}`). Add `?depth=1` for full nested objects:

```bash
curl -H "Authorization: Token $TOKEN" "$BASE/contracts/?depth=1" | jq '.results[].provider'
```

```json
{
  "id": "...",
  "name": "Acme Networks",
  "account_number": "ACM-12345",
  "support_phone": "+1-555-0100",
  ...
}
```

### Filtering

The plugin uses `NautobotFilterSet` — same filter syntax as core Nautobot models.

| Filter | Examples |
|---|---|
| Exact match | `?currency=USD` |
| Case-insensitive contains | `?name__ic=acme` |
| Date range | `?end_date__gte=2026-01-01&end_date__lte=2026-12-31` |
| FK by name (NaturalKey) | `?provider=Acme%20Networks` |
| FK by ID | `?provider=<uuid>` |
| Free-text search | `?q=acme` |
| Status (by slug or name) | `?status=active` |

### Creating a contract

```bash
# First, look up the IDs of the FK targets you'll reference
PROVIDER=$(curl -s -H "Authorization: Token $TOKEN" "$BASE/service-providers/?name=Acme%20Networks" | jq -r '.results[0].id')
STATUS=$(curl -s -H "Authorization: Token $TOKEN" "https://nautobot.example.com/api/extras/statuses/?name=Active" | jq -r '.results[0].id')

# Then POST
curl -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" -X POST "$BASE/contracts/" -d "{
  \"name\": \"New 2027 Agreement\",
  \"provider\": \"$PROVIDER\",
  \"status\": \"$STATUS\",
  \"start_date\": \"2026-12-01\",
  \"end_date\": \"2027-12-01\",
  \"recurring_cost\": \"5000.00\",
  \"currency\": \"USD\"
}"
```

### Bulk operations

Bulk endpoints work via the standard Nautobot conventions:

```bash
# Bulk create
curl -X POST "$BASE/contracts/" -d '[{...}, {...}]' ...

# Bulk delete (DELETE on the list endpoint with a list of IDs)
curl -X DELETE "$BASE/contracts/" -d '[{"id":"<uuid1>"}, {"id":"<uuid2>"}]' ...
```

### File uploads

`InvoiceAttachment` and `ContractAttachment` accept multipart/form-data:

```bash
curl -H "Authorization: Token $TOKEN" -X POST "$BASE/invoice-attachments/" \
  -F "invoice=<invoice-uuid>" \
  -F "file=@/path/to/invoice-2026-q1.pdf" \
  -F "description=Q1 2026 vendor PDF"
```

## Count fields per model

| Model | Field | Counts |
|---|---|---|
| ServiceProvider | `contract_count` | Contracts where `provider=this` |
| Contract | `invoice_count` | Invoices where `contract=this` |
| Contract | `assignment_count` | ContractAssignments where `contract=this` |
| Contract | `attachment_count` | ContractAttachments where `contract=this` |
| Invoice | `attachment_count` | InvoiceAttachments where `invoice=this` |

These are computed at query time via `count_related` annotations — no triggers, no denormalization. Change a child record and the parent's count is correct on the next request.

## Authentication

The plugin uses Nautobot's standard auth — no plugin-specific surface. To create or rotate tokens:

```bash
# From the UI: User menu (top right) → Profile → API Tokens
# From the shell:
nautobot-server shell -c "
from nautobot.users.models import Token
from django.contrib.auth import get_user_model
user = get_user_model().objects.get(username='your-user')
token, _ = Token.objects.get_or_create(user=user)
print(token.key)
"
```
