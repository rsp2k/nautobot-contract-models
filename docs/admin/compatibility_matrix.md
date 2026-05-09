# Compatibility Matrix

| App version | Nautobot range | Python | Database |
|---|---|---|---|
| 2026.5.9 | 3.0.0 – 3.x.x | 3.10, 3.11, 3.12 | PostgreSQL 12+, MySQL 8+ |

## Date-based versioning

This plugin uses [CalVer](https://calver.org/) (`YYYY.M.D`) rather than semver. The version is the date the release was tested against the Nautobot API surface, not a feature / breaking-change cadence.

Same-day fixes use a post-release suffix per PEP 440: `2026.5.9.1`, `2026.5.9.2`, etc.

## Supported Nautobot versions

The plugin targets Nautobot **3.x**. Specifically, it depends on:

- `nautobot.apps.NautobotAppConfig` (introduced in 3.0)
- `NautobotUIViewSet` and the modern detail-view component framework (`ObjectDetailContent`, `ObjectFieldsPanel`, `ObjectsTablePanel`)
- The Status framework (`StatusField`)
- The Job framework's `BooleanVar` / `IntegerVar` / `ObjectVar`
- The `extras_features` decorator with `graphql`, `webhooks`, `relationships`, `statuses`, etc.

If you're on Nautobot 2.x, this plugin will not import — the AppConfig surface and several decorators changed names between 2.x and 3.0.

## Database backends

PostgreSQL is the recommended backend. MySQL is supported but less thoroughly tested — file an issue if you hit a backend-specific bug.

## Python versions

The package wheels target 3.10 / 3.11 / 3.12. Python 3.13 is not yet listed in the classifiers; let the maintainer know if you'd like 3.13 support added.
