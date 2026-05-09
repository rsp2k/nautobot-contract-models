# Code Reference

This section is auto-generated from the source via `mkdocstrings`. Each page renders the docstrings from one module.

| Module | Contents |
|---|---|
| [Models](models.md) | Django ORM models — `Contract`, `ServiceProvider`, `Invoice`, `ContractAssignment`, `ContractAttachment`, `InvoiceAttachment`, `CostSnapshot` |
| [Cost Helpers](cost.md) | Per-currency aggregation: burn rate, renewal forecast, vendor spend, snapshots, history, anomaly detection |
| [Priority Helpers](priority.md) | URGENT / WARNING / INFO action-priority rubric |
| [Coverage Helpers](coverage.md) | Transitive coverage walk through Tenant / Location / Rack ancestry |
| [Jobs](jobs.md) | Background Jobs registered with the Celery worker |

## Reading the rendered docs

`mkdocstrings` pulls each module's class/function docstrings, signatures, and source links into the page. You see the same content as `pydoc nautobot_contract_models.cost`, but rendered.

For the editorial / "why this exists" context, read the [User Guide](../../user/app_overview.md) and [Using the App](../../user/app_use_cases.md) — the code reference sticks to surface-level documentation.
