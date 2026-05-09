# GraphQL reference

All six models register in Nautobot's GraphQL schema automatically. The interactive GraphiQL explorer is at `/graphql/`. POST queries to `/api/graphql/` with `Authorization: Token <key>`.

## Schema entry points

```graphql
{
  service_provider(id: $id) { ... }
  service_providers(name: $name) { ... }
  contract(id: $id) { ... }
  contracts(currency: $currency) { ... }
  invoice(id: $id) { ... }
  invoices(contract: $contract_id) { ... }
  contract_assignment(id: $id) { ... }
  contract_assignments(contract: $contract_id) { ... }
  contract_attachment(id: $id) { ... }
  contract_attachments(contract: $contract_id) { ... }
  invoice_attachment(id: $id) { ... }
  invoice_attachments(invoice: $invoice_id) { ... }
}
```

## Common queries

### Renewal report (replaces what the Job does in code)

```graphql
{
  contracts {
    name
    end_date
    recurring_cost
    currency
    provider { name }
    status { name }
  }
}
```

Filter to a specific window via `contracts(end_date__lte: "2026-12-31")` — the same filterset that backs the REST API.

### Contract → all related data in one call

```graphql
{
  contract(id: "f20de909-9feb-4b36-975b-e7e00a06b5a9") {
    name
    end_date
    recurring_cost
    currency
    provider {
      name
      account_number
      support_phone
    }
    status { name }
    tenant { name }
    invoices {
      invoice_number
      invoice_date
      total_amount
      paid_date
    }
    assignments {
      content_type { app_label model }
      object_id
    }
    attachments {
      file
      description
    }
  }
}
```

The reverse-FK fields (`invoices`, `assignments`, `attachments`) work because the parent declared `related_name=...` on the child's FK.

### Service provider → its contracts

```graphql
{
  service_providers {
    name
    account_number
    contracts {
      name
      end_date
      status { name }
    }
  }
}
```

### Filter by status

```graphql
{
  contracts(status: "active") {
    name
    end_date
  }
}
```

## Schema introspection

```bash
curl -s -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -X POST "https://nautobot.example.com/api/graphql/" \
  -d '{"query": "{ __schema { queryType { fields { name } } } }"}' \
  | jq '.data.__schema.queryType.fields[] | select(.name | test("contract|invoice|service_provider")) | .name'
```

## Caveats

- GraphQL responses always go through Nautobot's permission system — same `view_<model>` perms as the REST API.
- Filtering arguments are auto-generated from the `NautobotFilterSet` — the same filter syntax that the REST API uses.
- Pagination: GraphQL responses are unpaginated by default. For large queryset responses use the REST API's `?limit=N` instead.
- File-field URLs (`InvoiceAttachment.file`, `ContractAttachment.file`) return the storage-relative path. Prepend `MEDIA_URL` (typically `/media/`) to get a downloadable URL.
