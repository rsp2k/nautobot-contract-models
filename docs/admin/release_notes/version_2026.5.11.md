# v2026.5.11

Released **2026-05-11**. Coexistence fix for [`nautobot-app-device-lifecycle`](https://docs.nautobot.com/projects/device-lifecycle/en/latest/).

## What changed

Both `Contract.status` and `Invoice.status` now declare an explicit `related_name` so Django's reverse-accessor names don't collide with the device-lifecycle plugin when both apps are installed in the same Nautobot instance.

## Why

`nautobot-app-device-lifecycle` defines a `ContractLCM` model with a `StatusField`. Nautobot's default `StatusField.related_name` produces the same reverse accessor (`Status.contracts`) for both `Contract` and `ContractLCM`, which Django's system check rejects:

```
nautobot_contract_models.Contract.status: (fields.E304) Reverse accessor
  'Status.contracts' for 'nautobot_contract_models.Contract.status' clashes
  with reverse accessor for 'nautobot_device_lifecycle_mgmt.ContractLCM.status'.
```

Operators with both plugins installed couldn't boot Nautobot. This release unblocks them.

## How

Two AlterField operations in migration `0009_alter_status_related_name`:

- `Contract.status` → `related_name="contract_models_contracts"`
- `Invoice.status` → `related_name="contract_models_invoices"` (defensive; DLC has no Invoice equivalent today)

The migration is a Python-level rename only — no SQL runs, no column changes. Applies instantly.

## Upgrade path

```shell
pip install --upgrade nautobot-contract-models==2026.5.11
nautobot-server migrate
sudo systemctl restart nautobot nautobot-worker
```

If you already have both apps installed and were stuck at `SystemCheckError` on startup, this release fixes it. `nautobot-server check` should report clean afterward.

## Breaking changes

None at the data layer — `recurring_cost`, `billing_period`, all SLA fields, and every other field on `Contract` / `Invoice` are unchanged.

**Code-level:** If your custom code queries `Status.contracts.all()` or filters with `status__contracts__...`, you'll need to update to `Status.contract_models_contracts.all()` / `status__contract_models_contracts__...`. This is rare — most code accesses the FK forward (`contract.status`), which is unchanged.

## Out of scope (deferred)

This release does NOT add a unified analytics view across both apps. Operators with both installed see two separate "Contracts" surfaces in nav; our Cost Summary / Renewal Calendar / Action Required panels show only our `Contract` rows; DLC's `ContractLCM` rows are invisible to those analytics.

Building the bridge — read-only union of DLC contracts into our analytics, plus a one-way migration Job — is feasible but a feature add rather than a blocker fix. Open an issue if you want it prioritized.

## Tests

86 passing (82 from 2026.5.9 plus 4 new `test_collision.py` cases pinning the related_name configuration).
