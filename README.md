# nautobot-contract-models

A Nautobot content plugin that adds first-class models for **vendor contracts**, **invoices**, and **renewal tracking**, with the relationships needed to answer questions like:

- *Which contracts expire in the next 60 days?*
- *Which devices are covered by an active support contract, and which aren't?*
- *What did we pay last quarter for circuit X, and is it trending up?*

Inspired by [netbox-contract](https://github.com/mlebreuil/netbox-contract), but re-architected for Nautobot 3.x conventions: `PrimaryModel`, the Status framework, `Tenant`, ChangeLog, and the Job framework — rather than a line-by-line port.

## Status

**Phase 1 — Scaffold.** The package builds, the dev stack boots, and the plugin registers with Nautobot, but no models exist yet. Subsequent phases land:

| Phase | Adds |
|---|---|
| 1 (here) | Package skeleton, dev stack, AppConfig |
| 2 | `ServiceProvider`, `Contract`, `Invoice`, `ContractAssignment` (+ migrations) |
| 3 | UI views, forms, tables, filters, navigation |
| 4 | REST API + GraphQL |
| 5 | Renewal-alert Job + dashboard panel |
| 6 | Documentation pass |

See `PLAN.md` for the full breakdown.

## Models (Phase 2)

| Model | Role |
|---|---|
| `ServiceProvider` | The vendor / counterparty (account number, portal URL, support contact) |
| `Contract` | The master agreement (dates, recurring + one-time cost, status, tenant) |
| `Invoice` | A line item belonging to a contract (period, total, paid date) |
| `ContractAssignment` | Generic-FK link between a Contract and any Nautobot object (Device, Circuit, VirtualMachine, …) |

The `ContractAssignment` model uses Django's `ContentType` + `GenericForeignKey` so that one model handles all target types — no separate `ContractDevice`, `ContractCircuit`, `ContractVM` tables.

## Install (when v1 ships)

```bash
pip install nautobot-contract-models
```

Then add to `nautobot_config.py`:

```python
PLUGINS = ["nautobot_contract_models"]

PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        "renewal_window_days": 60,
    },
}
```

## Develop

```bash
cd development/
cp .env.example .env
$EDITOR .env
make build && make up
```

See `development/README.md` for the full bringup walkthrough and the four known gotchas (`COMPOSE_PROJECT_NAME` collision, volume-permission first-boot fix, etc.).

## Limitations (v1)

- **Single currency.** Costs are stored as `Decimal` with no currency field — pick yours and document it.
- **No approval workflows.** Nautobot's general `ApprovalQueue` covers this case if you need it.
- **No external sync.** Contracts live in Nautobot's database. If you need to read contracts from an external system (Hudu, ConnectWise, Lansweeper), build a separate SSoT plugin.
- **No per-line-item invoice breakdown.** One `Invoice` row = one billing period. Use Nautobot custom fields or notes if you need finer granularity.
- **No multi-currency rate tracking.** If you need to report contract value in a base currency, do it at query time.

## License

TBD with the operator.

## Acknowledgements

The data model and many of the lessons come from [netbox-contract](https://github.com/mlebreuil/netbox-contract) by Marc Lebreuil. Tooling and dev-stack patterns mirror the operator's [nautobot-plugin-ssot-hudu](https://github.com/rsp/nautobot-plugin-ssot-hudu).
