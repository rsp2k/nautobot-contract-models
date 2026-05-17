# Release Notes

This section tracks released versions of `nautobot-contract-models`. Versions follow [CalVer](https://calver.org/) — the date the package was tested against the Nautobot API surface.

| Version | Released | Highlights |
|---|---|---|
| [v2026.5.17](version_2026.5.17.md) | 2026-05-17 | Phase 20: iCal export, Device-detail Active Contracts panel, Vendor Concentration Risk dashboard, Coverage Drift report. |
| [v2026.5.12](version_2026.5.12.md) | 2026-05-12 | Absorb DLM's contracts: one-way `MigrateContractLCMToContract` Job + opt-in `hide_dlm_contracts_nav` flag. |
| [v2026.5.11](version_2026.5.11.md) | 2026-05-11 | Coexistence fix: namespace `related_name` on `Contract.status` / `Invoice.status` so the app works alongside `nautobot-app-device-lifecycle`. |
| [v2026.5.9](version_2026.5.9.md) | 2026-05-09 | First public release. Sixteen-phase build. |

## Versioning policy

- **Same-day fixes** use a post-release suffix per PEP 440: `2026.5.9.1`, `2026.5.9.2`, etc.
- **Schema-changing releases** are called out explicitly in their version notes — read those before running `nautobot-server migrate`.
- **Breaking API changes** are rare; when they happen, the version note describes the operator-side action required.
