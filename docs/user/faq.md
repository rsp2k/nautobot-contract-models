# Frequently Asked Questions

## Why a separate plugin instead of using Nautobot's built-in custom fields?

Custom fields work for "tag a contract number on every device" but break down for any of the analytics this plugin provides. There's no way to express "find all devices whose Tenant has a contract ending within 30 days" with custom fields — they don't carry the FK structure or the ChangeLog history that makes those queries possible.

## Why doesn't the burn rate match my finance system?

Two likely reasons:

1. **billing_period mismatch.** Migration `0007` defaults every existing contract to `billing_period='monthly'`. If you have annual contracts already in the database, their `recurring_cost` is being treated as a monthly figure — over-counting by 12x. Edit those contracts after upgrade. See [Install](../admin/install.md#upgrading-from-pre-phase-8).

2. **Currency mixing.** The plugin never sums across currencies. If your finance system reports a single "total spend" and yours doesn't, that's because we're showing per-currency rows. The dashboard is intentionally honest about this — see [Why no FX conversion?](#why-no-fx-conversion).

## Why no FX conversion?

Summing $5,000 USD + €4,000 EUR into a single number is wrong in three different ways:

- Which exchange rate? Spot? Booked? Internal?
- As of when? Today? When the contract was signed? Average over the term?
- For which purpose? Cash-flow forecasting? GAAP reporting? Procurement comparison?

Pushing the question up to whoever owns FX in your org (probably finance) is the correct conservative behavior. The plugin's helpers return `dict[currency, Decimal]` and let the dashboard render each currency on its own row.

## Why a generic FK on `ContractAssignment` instead of M2M to Device?

A vendor support contract typically covers a *fleet* — devices, circuits, virtual machines, sometimes a whole tenant. Modeling it as a Device M2M would mean separate models for every assignable target type. The generic FK lets one `ContractAssignment` row cover any Nautobot model with a UUID PK (which is every Nautobot model).

## Why doesn't deleting a Contract delete its CostSnapshot history?

Snapshots are point-in-time fleet aggregates, not per-contract rows. They have no FK to Contract on purpose — historical "we used to spend $X with that vendor" data should survive contract deletion. If we linked them, deleting a contract destroys exactly the history operators want to keep.

## Why are the Job log lines tagged `[URGENT]` / `[WARNING]` / `[INFO]`?

The `Check upcoming renewals` Job uses the same priority rubric as the Action Required dashboard surface (centralized in `priority.action_priority()`). Tagging the log line with the tier means an operator scanning JobLogEntry rows can find the URGENT lines as fast as the dashboard's URGENT bucket.

## Can I use this plugin without the cost analytics?

Yes. The cost analytics are additive — if you don't set `recurring_cost`, `billing_period`, or `term_months`, the cost surface (Cost Summary panel, Renewal Forecast panel, Cost History page) just shows zero / empty. The core Contract / Invoice / Assignment models work fine on their own.

## Why are notes auto-wired but I have to opt in to other features?

Nautobot's `NautobotUIViewSetRouter` auto-registers `<model>/<pk>/notes/`, `<model>/<pk>/changelog/`, `<model>/<pk>/contacts/`, and a few others for every viewset it knows about. Other features (custom fields, relationships, statuses, webhooks, GraphQL) require explicit `extras_features("...")` registration on the model — different mechanism. The auto-wired ones come along for free.

## Where do I report bugs / request features?

Open an issue on the [GitHub repository](https://github.com/rpmcg/nautobot-contract-models/issues).
