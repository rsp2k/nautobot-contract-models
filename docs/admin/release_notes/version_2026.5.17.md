# v2026.5.17

Released **2026-05-17**. Phase 20: four Tier A operator-facing convenience features.

## What changed

Four new surfaces that compound on the existing infrastructure to meet operators where they already work:

- **iCal calendar export** — subscribe in Outlook / Google Calendar / iCloud / any RFC 5545 client. Contract end dates appear as all-day events next to actual meetings.
- **Device-detail "Active Contracts" panel** — every Nautobot Device page now shows the contracts covering it (direct or via Tenant / Location / Rack ancestry), so contract coverage shows up where operators are already debugging.
- **Vendor Concentration Risk home dashboard panel** — per-currency top-vendor share, with a threshold flag when any vendor exceeds the configured concentration percentage.
- **Coverage Drift report** — surface devices that *lost* contract coverage in a configurable window (or gained coverage — operational sanity check that new contracts landed).

## New surfaces

| URL / view | What it does |
|---|---|
| `/plugins/contracts/contracts.ics` | iCal feed of active contract renewal dates. Supports session auth (browser) and a per-user URL-param token. |
| `/plugins/contracts/ical-token/` | Token management page: view + copy subscription URL, regenerate to revoke. |
| `/plugins/contracts/reports/coverage-drift/` | Drift comparison — devices that gained or lost coverage over the configured window. |
| `Home → Vendor Concentration` | Per-currency top-vendor share, with concentration risk flag. |
| `Devices → <any device> → right side` | Active Contracts panel showing direct + transitive coverage. |
| `Apps → Jobs → Capture coverage snapshot` | Persists per-device coverage state; feed for the drift report. Schedule weekly. |

## New PLUGINS_CONFIG keys

```python
PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        # Existing keys unchanged...
        "renewal_window_days": 60,
        "hide_dlm_contracts_nav": False,

        # NEW in 2026.5.17:
        "vendor_concentration_threshold_pct": 50,  # 0–100; trips the flag on the Vendor Concentration panel
    },
}
```

## How — Feature A: iCal subscription

1. Visit `/plugins/contracts/ical-token/`. The page auto-creates a per-user access token on first visit.
2. Copy the displayed subscription URL (it has `?token=<32-char-secret>` appended).
3. Paste into your calendar app's "Subscribe to calendar" dialog:
    - **Outlook**: Add Calendar → Subscribe from web.
    - **Google Calendar**: Other calendars → From URL.
    - **iCloud**: File → New Calendar Subscription.

Contract end dates appear as all-day events. The feed re-fetches periodically; deleted/expired contracts disappear automatically on next sync.

**Why token-in-URL not Bearer auth**: Calendar clients don't carry session cookies or Authorization headers — they send a single GET with whatever auth was in the original URL. The token-in-URL pattern is the de facto standard for self-hosted calendar subscriptions.

**Security model**: The token is opaque (32 URL-safe characters), per-user, and rotatable. Treat the subscription URL like a password — anyone with it can see your contracts' end dates. Regenerate immediately if leaked (invalidates the previous URL).

## How — Feature B: Device-detail Active Contracts panel

Automatic — no operator action needed. Visit any Device detail page. A new "Active Contracts" panel appears on the right side showing contracts that cover the device:

- **Direct**: ContractAssignment with `content_type=dcim.device, object_id=<this device>`.
- **via Tenant / Location / Rack / parent Device**: ancestry walk; the same `has_active_coverage` semantics used by the Coverage Gaps Job.

The "Source" column shows the path: `direct`, `via Tenant: ACME Corp`, `via Location: SF-HQ`, etc.

## How — Feature C: Vendor Concentration Risk panel

Automatic — no operator action needed. On the home dashboard between Cost Summary and Renewal Forecast, you'll see per-currency top-vendor percentages. A currency where one vendor's share exceeds the threshold (default 50%) gets an amber "concentration risk" badge.

Adjust the threshold by setting `vendor_concentration_threshold_pct` in `PLUGINS_CONFIG`. Range 0–100. Set to 100 to effectively disable the flag without removing the panel.

## How — Feature D: Coverage Drift report

1. *Apps → Jobs → "Capture coverage snapshot"* — enable + run. The Job iterates every Device and writes one `CoverageSnapshot` row per device for today's coverage state.
2. Schedule the Job weekly (Apps → Jobs → Scheduled Jobs) so drift comparison always has historical data.
3. Visit `/plugins/contracts/reports/coverage-drift/`. The window selector controls the comparison range (7 / 30 / 90 / 180 / 365 days, default 30).

The report shows:
- **Lost coverage** (red rail): devices that were covered N days ago and aren't now.
- **Newly covered** (green rail): inverse — sanity check that newly-signed contracts landed.

Devices that didn't exist in the baseline snapshot are excluded (no comparison point), so adding new devices doesn't generate noise.

## Upgrade path

```shell
pip install --upgrade nautobot-contract-models==2026.5.17
nautobot-server migrate
sudo systemctl restart nautobot nautobot-worker
```

Migration `0010_icalaccesstoken_coveragesnapshot` adds two new models. No data migration; instant on any size database.

## Breaking changes

None. All four features are additive:
- iCal token auto-creates on first profile visit; no proactive provisioning required.
- Device-detail panel renders empty for devices with no coverage — no error state.
- Vendor concentration panel renders an info row if no active contracts exist.
- Coverage drift renders an "instructional" empty state if the Job hasn't run yet.

## Tests

134 passing (98 from 2026.5.12 plus 36 new):
- `test_ical_export.py` (14 tests)
- `test_template_content.py` (6 tests)
- `test_vendor_concentration.py` (5 tests)
- `test_coverage_drift.py` (5 tests)

Test-environment fixes shipped with this release:
- Dev `nautobot_config.py` adds `nautobot.example.com` to `ALLOWED_HOSTS` so Nautobot's test client (`NautobotTestClient` uses `SERVER_NAME=nautobot.example.com`) doesn't get 400-rejected.
- Dev `docker-compose.yml` switches `NAUTOBOT_DB_HOST` from `postgres` to the fully-qualified `nautobot-contract-models-postgres` to avoid cross-compose-stack DNS collisions on the shared `caddy` network.

## Out of scope (deferred)

- **iCal RRULE** for auto-renew contracts (yearly recurrence). Defer until operator requests.
- **Per-tenant iCal filtering**. v1 ships "every contract the user can see"; multi-tenant operators wanting strict isolation: defer to feedback.
- **CoverageSnapshot REST API** read-only viewset (mirrors CostSnapshot's API). Not blocking the drift view; nice-to-have.
- **CoverageSnapshot retention Job**. 52K rows/year for 1000-device fleets is fine; revisit at 10×.
- **Vendor concentration with FX conversion**. Still no FX in v1.
