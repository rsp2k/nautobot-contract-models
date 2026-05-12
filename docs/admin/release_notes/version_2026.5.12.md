# v2026.5.12

Released **2026-05-12**. Absorb DLM's contracts — one-way migration Job + opt-in nav hide.

## What changed

Two pieces of operator-visible functionality build on the Phase 18 coexistence fix:

1. **A new Job**: `MigrateContractLCMToContract` (under *Apps → Jobs → Contracts*) copies every `ContractLCM` row from `nautobot-app-device-lifecycle-mgmt` into our `Contract` model. Idempotent and one-way.
2. **An opt-in PLUGINS_CONFIG flag**: `hide_dlm_contracts_nav` removes DLM's `Contracts` group from the **Device Lifecycle** sidebar so operators see one canonical contracts surface — ours.

DLM's data, URLs, REST API, and other nav groups (Hardware Notices, Software Lifecycle, Reports) remain untouched.

## Why

After Phase 18 unblocked coexistence, operators with both plugins installed still saw two parallel "Contracts" surfaces in the same Nautobot. DLM's `ContractLCM` is structurally a subset of our `Contract` (no recurring/billing-period, no SLA fields, no auto_renew/notice_period); DLM's own `DLMToNautobotCoreModelMigration` Job explicitly *skips* ContractLCM because Nautobot core has no Contract destination. We fill that gap — our plugin is the natural destination DLM never had.

## How

### Field mapping

`ContractLCM` → `Contract`:

| DLM field | Our field | Notes |
|---|---|---|
| `name` | `name` | direct |
| `provider` (ProviderLCM) | `provider` (ServiceProvider) | matched by name; auto-created with the default `by_name` strategy |
| `status` (StatusField) | `status` (StatusField) | falls back to "Active" if DLM's status isn't valid for our Contract |
| `number` | `contract_number` | direct |
| `start` | `start_date` | direct |
| `end` | `end_date` | direct |
| `cost` | `recurring_cost` | interpreted per the `default_billing_period` Job var (default Monthly) |
| `currency` | `currency` | direct; default `USD` if blank |
| `support_level` (free-text) | `coverage_hours` + `response_time` (enums) | best-effort regex match — see below |
| `contract_type` (free-text) | `contract_type` (enum) | best-effort regex match |
| `devices` (M2M) | `ContractAssignment` rows | one per device, `content_type=dcim.Device` |
| `comments` | `comments` | direct |

### Best-effort free-text → enum mapping

DLM stores `support_level` and `contract_type` as free strings. We have enums. The Job runs a regex pass and warns-and-leaves-blank when no pattern matches:

- `"24x7 with 4-hour response"` → `coverage_hours="24x7"`, `response_time="4h"`
- `"8x5xNBD"` → `coverage_hours="8x5_nbd"`, `response_time="nbd"`
- `"Hardware Maintenance"` → `contract_type="hardware"`
- `"Premium Gold Tier"` → leaves both blank, logs a warning per row

Operators review the Job's warning log entries and manually fix unmappable rows in our UI afterward.

### Idempotency

Each successfully-migrated `ContractLCM` gets stamped with a Nautobot custom field `migrated_to_contract_models=True`. Re-running the Job excludes already-stamped rows. The same pattern DLM's own `model_migration.py` uses for its `migrated_to_core_model_flag`.

### One-way

Source `ContractLCM` rows are stamped but **not deleted**. Operators delete from DLM's UI when comfortable.

### Job variables

| Variable | Default | Meaning |
|---|---|---|
| `dry_run` | `True` | Log planned actions without writing. Run dry first to verify. |
| `default_billing_period` | `Monthly` | How to interpret DLM's flat `cost` field — recurring at this cadence. |
| `provider_match_strategy` | `Match by name; create ServiceProvider if missing` | Alternative: `Match by name; skip the contract if no ServiceProvider matches`. |

### Opt-in nav hide

In `PLUGINS_CONFIG`:

```python
PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        "hide_dlm_contracts_nav": True,  # default False
    },
}
```

When `True` *and* `nautobot-app-device-lifecycle-mgmt` is installed, our `AppConfig.ready()` connects a `request_started` signal that — on the first HTTP request after startup — surgically removes DLM's `Contracts` group from the `Device Lifecycle` nav tab. DLM's `Hardware Notices`, `Software Lifecycle`, and `Reports` groups survive.

We defer the removal to `request_started` rather than firing it directly from `ready()` because Django/Nautobot load plugins in `INSTALLED_APPS` order — if your plugin lists `nautobot_contract_models` before `nautobot_device_lifecycle_mgmt`, our `ready()` runs before DLM has registered its nav, and a direct removal would be a no-op. The lazy approach is robust regardless of `PLUGINS` ordering.

## Upgrade path

Operators with both plugins installed:

```shell
pip install --upgrade nautobot-contract-models==2026.5.12
nautobot-server migrate
sudo systemctl restart nautobot nautobot-worker
```

Then in the UI:

1. *Apps → Installed Apps → Jobs* — find the new "Migrate ContractLCM → Contract" Job under the Contracts group; click **Edit** and check **Enabled** (Nautobot's job-permission default is disabled).
2. Run with `dry_run=True` first; inspect the JobLogEntries for the planned mapping and any `[unmapped]` warnings.
3. Run with `dry_run=False` to commit.
4. (Optional) Add `"hide_dlm_contracts_nav": True` to `PLUGINS_CONFIG["nautobot_contract_models"]` and restart `nautobot` — DLM's Contracts sidebar group disappears.

## Breaking changes

None. The migration is opt-in (operator must enable the Job and run it). The nav hide is opt-in (operator must set the flag).

DLM keeps its DB, REST API, and other nav groups working as before. Existing scripts hitting DLM's `/api/plugins/nautobot-device-lifecycle-mgmt/contract/...` endpoints continue to work.

## Out of scope (deferred)

- **DLM's `DeviceContractLCM` template-content panel** (the contracts table injected into Device detail). Even with nav hidden, operators may still see this panel. Suppressing template content cleanly requires monkey-patching DLM or asking DLM upstream.
- **URL redirect middleware** rewriting DLM's contract URLs to ours. Avoided because it would break DLM REST API consumers and external bookmarks.
- **Two-way sync**. One-way only — updates to our `Contract` do NOT propagate back to `ContractLCM`.
- **Upstream PR** on `nautobot-app-device-lifecycle-mgmt` adding a `DISABLE_CONTRACTS_SURFACE` flag — the right long-term answer; this release ships the pragmatic in-between.

## Tests

98 passing (86 from 2026.5.11 plus 12 new across `test_migration_job.py` and `test_nav_hide.py`). New tests gate on `apps.is_installed('nautobot_device_lifecycle_mgmt')` — they run in the dev container (DLM pinned via dev image) and skip cleanly on a host that doesn't have DLM installed.
