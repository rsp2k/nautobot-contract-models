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

If you have both this plugin and `nautobot-app-device-lifecycle-mgmt` (DLM) installed, you have two opt-in features available:

- A one-way idempotent **Migrate ContractLCM → Contract** Job that copies DLM's `ContractLCM` rows into our `Contract` model (including device M2M → polymorphic `ContractAssignment`).
- The **`hide_dlm_contracts_nav`** PLUGINS_CONFIG flag (see the table above) that removes DLM's Contracts sidebar group so operators see one canonical contracts surface — ours.

Step-by-step walkthrough with screenshots: **[Coexistence with `nautobot-app-device-lifecycle`](dlm_coexistence.md)**.

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
