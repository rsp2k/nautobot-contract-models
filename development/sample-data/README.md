# Sample CSV data

Files in this directory are for *operator demos and quick-start imports*, not
for the test suite. They exercise every Contract field so you can paste-and-go
or use them as templates for your own bulk loads.

## Files

| File | Use |
|---|---|
| `contracts.csv` | Six representative contracts: hardware support, SaaS subscriptions, a Microsoft EA, a DNS service, a multi-year warranty, and a quarterly-billed firewall SLA. Mixes USD + EUR; covers monthly/quarterly/annual/one-time billing periods. |

## Importing

Two ways to load a CSV:

**1. Web UI** — `Contracts → Contracts → Import` (or visit
`/plugins/contracts/contracts/import/`). Paste the CSV body or use the
file-upload tab. Nautobot auto-renders the field reference table from the
serializer; required vs optional is shown for every column.

**2. CLI** —

```bash
make shell  # bash inside the dev container

cat /opt/plugin/development/sample-data/contracts.csv | nautobot-server import_objects \
    --content-type nautobot_contract_models.contract \
    --format=csv -
```

## Format quirks

- **FK lookups by natural key.** `provider=Acme Networks` works because the
  ServiceProvider's natural key is its `name`. Same for `status=Active` (a
  custom Status object). UUIDs also work.
- **Booleans.** `auto_renew` accepts the literals `true` / `false`. Numeric
  0/1 do *not* work.
- **Dates.** `YYYY-MM-DD` only. The CSV importer doesn't sniff alternate
  formats.
- **billing_period.** Must be one of `monthly` / `quarterly` / `semiannual`
  / `annual` / `one_time`. Capitalization matters.
- **Empty cells.** Leave blank for nullable fields (`tenant`, `term_months`,
  `notice_period_days`). Don't write `null` or `None` — the parser treats
  them as literal strings.
- **One-time contracts.** Set `recurring_cost=0`, put the actual price in
  `one_time_cost`, and `billing_period=one_time`. Burn-rate panels exclude
  them; total-contract-value still counts them.
