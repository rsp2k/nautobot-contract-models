# Installing the App in Nautobot

This page covers **install** and **configure** for `nautobot-contract-models`.

## Prerequisites

- Nautobot 3.0.0 or higher
- Database: PostgreSQL or MySQL
- Python 3.10+

!!! note
    Check the [compatibility matrix](compatibility_matrix.md) for the supported Nautobot version range.

## Install Guide

The app is published on PyPI. Install with pip:

```shell
pip install nautobot-contract-models
```

To make sure the app is reinstalled on Nautobot upgrades, add it to your `local_requirements.txt`:

```shell
echo nautobot-contract-models >> local_requirements.txt
```

## Enable the App

Edit `nautobot_config.py`:

- Append `"nautobot_contract_models"` to `PLUGINS`.
- Optionally add a `"nautobot_contract_models"` block to `PLUGINS_CONFIG`.

```python
# In nautobot_config.py

PLUGINS = [
    "nautobot_contract_models",
]

PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        # Default window for the renewal-check Job and the home dashboard
        # "Upcoming Renewals" panel. Defaults to 60 days.
        "renewal_window_days": 60,
    },
}
```

Then run migrations and collect static:

```shell
nautobot-server migrate
nautobot-server collectstatic --noinput
```

Restart the Nautobot web service AND the Celery worker:

```shell
sudo systemctl restart nautobot nautobot-worker
```

The worker restart is important — newly-discovered Jobs won't appear until the worker re-reads the registry.

## Verify the install

1. Visit `/apps/installed-apps/` and confirm `nautobot_contract_models` is listed.
2. Visit `/plugins/contracts/contracts/` — you should see the (empty) contract list.
3. Visit `/jobs/` and look under the *Contracts* group for five jobs:
    - Check upcoming renewals
    - Find devices without contract coverage
    - Monthly cost report
    - Capture cost history snapshot
    - Detect cost anomalies

## App Configuration

| Setting | Default | Description |
|---|---|---|
| `renewal_window_days` | `60` | Days from today to look ahead. Drives the renewal-check Job's default and the Renewal Forecast home dashboard panel. |
| `hide_dlm_contracts_nav` | `False` | When `True` AND `nautobot-app-device-lifecycle-mgmt` is installed, surgically removes DLM's `Contracts` group from the **Device Lifecycle** sidebar. Operator-controlled; off by default. See [Coexistence with nautobot-app-device-lifecycle](#coexistence-with-nautobot-app-device-lifecycle). |

## Coexistence with `nautobot-app-device-lifecycle`

`nautobot-app-device-lifecycle-mgmt` (DLM) ships a `ContractLCM` model that overlaps with our `Contract`. Since v2026.5.11 the two plugins coexist cleanly in the same Nautobot. v2026.5.12 adds two opt-in features for operators who want our `Contract` to be the canonical contracts surface:

### 1. Migrate ContractLCM data into our model

Run the **Migrate ContractLCM → Contract** Job (under *Apps → Jobs → Contracts*):

1. *Apps → Jobs → "Migrate ContractLCM → Contract"* — click the row, then **Edit** → check **Enabled** → **Save**. (Nautobot's job-permission default is disabled.)
2. Click **Run Job**.
3. Set `dry_run=True` for the first invocation. Read the JobLogEntry output:
    - Counts: `migrated`, `skipped`, `assignments` (devices converted into `ContractAssignment` rows), `warnings`.
    - Per-row `[dry-run] Would migrate...` lines.
    - `[unmapped]` warnings for rows whose `support_level` or `contract_type` free-text didn't match any known pattern. Fix the source values in DLM's UI, or accept that those fields land blank.
4. Re-run with `dry_run=False` to commit.
5. Re-run a third time — verify `migrated: 0` (idempotency stamp prevents duplicates).

Each migrated `ContractLCM` is stamped with a custom field `migrated_to_contract_models=True`. Source rows are **not deleted** — operators delete from DLM's UI when comfortable that the migration is correct.

Job options:

| Variable | Default | Meaning |
|---|---|---|
| `dry_run` | `True` | Log planned actions without writing. Always run dry first. |
| `default_billing_period` | `Monthly` | DLM's `ContractLCM.cost` is a flat decimal with no cadence — we interpret it as recurring at this cadence. Set to `Annual` if your DLM contracts stored annual prices. |
| `provider_match_strategy` | `Match by name; create ServiceProvider if missing` | Alternative: `Match by name; skip the contract if no ServiceProvider matches`. |

### 2. Hide DLM's Contracts sidebar group

After migration, set the opt-in flag:

```python
# nautobot_config.py
PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        "hide_dlm_contracts_nav": True,
    },
}
```

Restart Nautobot. DLM's `Contracts` and `Vendors` sub-items disappear from the **Device Lifecycle** sidebar; `Hardware Notices`, `Software Lifecycle`, and `Reports` remain.

DLM's data, URLs (`/plugins/nautobot-device-lifecycle-mgmt/contract/...`), REST API, and `DeviceContractLCM` template-content panel on the Device detail page all keep working — only the sidebar nav is affected. Operators with scripts or external integrations hitting DLM's contract endpoints don't break.

## Upgrading from pre-Phase-8

Migration `0007_contract_billing_period` defaults every existing `Contract` to `billing_period='monthly'`. If you have **annual** or **quarterly** contracts already in the database, their `recurring_cost` will be interpreted as a monthly figure after upgrade — over-counting the burn rate panels by 12x (annual) or 3x (quarterly).

Two ways to fix:

**Option 1 — bulk edit via the UI**

1. Visit `/plugins/contracts/contracts/?billing_period=monthly`
2. Select contracts that should be annual / quarterly
3. Click **Edit Selected** and change `billing_period`

**Option 2 — Django ORM (faster for many contracts)**

```python
# nautobot-server shell
from nautobot_contract_models.models import Contract
Contract.objects.filter(name__icontains="EA").update(billing_period="annual")
Contract.objects.filter(name__icontains="quarterly").update(billing_period="quarterly")
```

After the fix, run **Capture cost history snapshot** to refresh the trend baseline.

## Static files

The plugin ships its own static CSS files for the Renewal Calendar, Action Required, and Cost History pages. `nautobot-server collectstatic` picks these up automatically; no additional configuration needed.

## Removing the app

See [Uninstall](uninstall.md).
