# Upgrading the App

Upgrading `nautobot-contract-models` follows the same pattern as any Nautobot plugin.

## Standard upgrade path

```shell
pip install --upgrade nautobot-contract-models
nautobot-server migrate
nautobot-server collectstatic --noinput
sudo systemctl restart nautobot nautobot-worker
```

The worker restart matters — without it, newly added Jobs (or changes to existing Jobs) won't be picked up.

## Notable migrations to be aware of

### Migration `0007_contract_billing_period` (Phase 8)

Adds `Contract.billing_period` and defaults existing rows to `monthly`. If you have annual / quarterly contracts already in the database, edit them after upgrade — otherwise the cost analytics panels will over-count. See [Install — Upgrading from pre-Phase-8](install.md#upgrading-from-pre-phase-8) for the exact steps.

### Migration `0008_costsnapshot` (Phase 13)

Creates the `CostSnapshot` table for cost-history time series. No data migration; the table starts empty. Schedule the **Capture cost history snapshot** Job after upgrade to start collecting data.

## Verifying after upgrade

1. **System check** — `nautobot-server check` should pass clean.
2. **Migration check** — `nautobot-server makemigrations --check --dry-run nautobot_contract_models` should report "No changes detected".
3. **Job registry** — visit `/jobs/?grouping=Contracts` and confirm all expected Jobs are listed.
4. **Dashboard panels** — the home page should show Contracts / Action Required / Coverage Gaps / Cost Summary / Renewal Forecast panels (all four added by this app).

## Rolling back

The plugin's migrations are Django-standard. To roll back to a previous schema:

```shell
nautobot-server migrate nautobot_contract_models <target-migration-number>
pip install nautobot-contract-models==<previous-version>
```

Be aware that rolling back past `0008_costsnapshot` will drop the snapshot table — you'll lose any captured cost history.

## Date-based versioning

This plugin uses [CalVer](https://calver.org/) (`YYYY.M.D`) rather than semver. The version reflects when the package was tested against the Nautobot API surface, not a feature/breaking-change cadence. Upgrades within a CalVer year-month are typically backward-compatible; year-major changes may include schema migrations worth reading the release notes for.
