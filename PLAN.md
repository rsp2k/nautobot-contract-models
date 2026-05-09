# nautobot-contract-models — Plan

## Mission

Add first-class **Contract**, **Invoice**, and **ServiceProvider** models to Nautobot, with the relationships needed to track which contracts cover which physical/logical resources (Devices, Circuits, VirtualMachines, etc.) and surface upcoming renewals.

The motivating use case: a network operator (MSP, IT department, or service provider) wants to answer questions like:

- *Which contracts expire in the next 60 days?*
- *Which devices are covered by an active support contract, and which aren't?*
- *What did we pay last quarter for circuit X, and is the cost trending up?*
- *Who do I call when device Y has a hardware failure?*

Today these answers live in spreadsheets, ticketing-system custom fields, or scattered wiki pages. This plugin centralizes them in the same database where the network topology already lives, with the correct foreign keys to make the joins trivial.

## Source of inspiration

[netbox-contract](https://github.com/mlebreuil/netbox-contract) is a long-standing NetBox plugin (~8K LOC) that does this for NetBox. Its data model is a good starting point. We're not porting line-by-line — we're stealing the model and the lessons, and re-implementing for Nautobot 3.x's conventions.

What netbox-contract has (broadly):
- Contract (the master agreement)
- ContractAssignment (M2M-via-through-model linking contracts to NetBox objects)
- Invoice (line items belonging to a contract)
- ServiceProvider (the vendor / counterparty)
- AccountingDimension (cost-center / GL-account tagging)

What we'll do differently for Nautobot 3.x:
- Use Nautobot's `PrimaryModel` (gives us ChangeLog, ContentType-based generic relations, custom-fields support, tags, etc. for free)
- Use Nautobot's existing `Tenant` for ownership; don't reinvent
- Use Nautobot's existing `Status` framework for contract state (Active/Expired/Cancelled)
- Use Nautobot's `JobModel` framework for renewal alerts (cron-runnable, log-tracked)
- Probably skip AccountingDimension v1 — too org-specific; let operators add via custom fields

## Phases

### Phase 1 — Scaffold (1 session)

Goal: package builds, dev stack boots, plugin registers as a Nautobot App.

- `git init`
- `pyproject.toml` (uv + hatchling + CalVer + ruff)
- `src/nautobot_contract_models/__init__.py` with `NautobotAppConfig`
- `development/` dev stack mirroring the nautobot-ssot-hudu pattern (Dockerfile + compose + Makefile + nautobot_config + .env.example)
- Empty `migrations/` directory
- Empty `models/`, `views/`, `forms/`, `tables/`, `filters/`, `api/` directories
- `tests/conftest.py` with the Nautobot-mocking pattern
- README with mapping table placeholder
- First commit: "Initial scaffold"

**Acceptance:** `make build && make up` boots a Nautobot dev instance, `nautobot-server shell -c "import nautobot_contract_models"` succeeds, plugin appears in Nautobot's `/apps/installed-apps/` listing.

### Phase 2 — Core models + migration (1 session)

Goal: real Django models, real migrations, real DB tables.

- `models/provider.py` — `ServiceProvider(PrimaryModel)`: name, account_number, contact info, portal_url, support_phone, notes
- `models/contract.py` — `Contract(PrimaryModel)`: name, contract_number, provider (FK), tenant (FK), start_date, end_date, renewal_terms, recurring_cost (Decimal), one_time_cost (Decimal), status (Status FK), description
- `models/invoice.py` — `Invoice(PrimaryModel)`: contract (FK), invoice_number, period_start, period_end, total_amount (Decimal), invoice_date, paid_date (nullable), status, description
- `models/assignment.py` — `ContractAssignment(BaseModel)`: contract (FK), content_type (FK ContentType), object_id (UUIDField), object (GenericForeignKey). Lets a Contract attach to a Device, Circuit, VirtualMachine, etc. without a model-per-target-type.
- Generate migrations: `nautobot-server makemigrations nautobot_contract_models`
- Tests: model field shape, FK cascade behavior, Status content_type registration, GenericForeignKey resolution

**Acceptance:** migrations apply cleanly to a fresh DB, you can create a Contract via `nautobot-server shell` and see it in `/admin/`, ContractAssignment to a real Device is queryable both forward and backward (`device.contract_assignments.all()` and `contract.assignments.all()`).

### Phase 3 — Forms + tables + UI views (1 session)

Goal: Nautobot UI shows the new models — list view, detail view, edit forms.

- `forms/` — `ContractForm`, `InvoiceForm`, `ServiceProviderForm`, `ContractAssignmentForm`
- `tables/` — django-tables2 `ContractTable`, etc.
- `filters/` — django-filter classes for list-view filtering
- `views/` — class-based views inheriting from `nautobot.core.views.generic.ObjectListView`, `ObjectDetailView`, `ObjectEditView`, `ObjectDeleteView`
- `urls.py` — wire the views
- `navigation.py` — add a "Contracts" nav menu group with sub-items
- Templates if needed (`templates/nautobot_contract_models/`)

**Acceptance:** Logging into Nautobot, the user sees a "Contracts" menu, can create a Contract via the UI, attach it to an existing Device via ContractAssignment, see the Contract listed under that Device's detail page (via the inverse generic relation on `nautobot.dcim.Device`).

### Phase 4 — REST API refinement + GraphQL (~half session)

**Note:** Phase 3 turned out to require the api/urls.py wiring as a hard
prerequisite — Nautobot's post-save signal serializes new objects into the
ChangeLog using the configured serializer, and our serializer's
hyperlinked-relationship fields try to reverse API URLs even when no user
is hitting the API. So `api/serializers.py`, `api/urls.py`, and the
viewset registration that produces both UI and API routes all landed in
Phase 3. Phase 4 is now scoped to the *refinement* on top:

- `api/serializers.py` — replace `fields = "__all__"` with explicit field
  lists, add nested-relationship serializers (e.g. expand `provider` into
  the full ServiceProvider blob on Contract reads, not just a hyperlink)
- Custom API actions if any (e.g. `Contract.viewset.expiring/`)
- GraphQL types: usually auto-generated by Nautobot's GraphQL infra if the
  model is registered correctly; verify they appear in the schema
- Tests for API endpoints (Nautobot's `APIViewTestCases` mixin handles
  most of this)

**Acceptance:** `curl /api/plugins/contracts/contracts/` returns JSON
with nested provider/tenant data (not just hyperlinks); GraphQL schema
query for `contracts` works.

### Phase 5 — Renewal-alert Job + dashboard panel (~half session)

- `jobs.py` — A `RenewalCheckJob(Job)` that finds contracts expiring within a configurable window and creates Nautobot notifications, writes to JobLogEntry, optionally sends webhooks
- Configurable via PLUGINS_CONFIG: `renewal_window_days = 60` (default), notification channel (Nautobot notifications, Slack via webhook, etc.)
- A small `panels/` template that renders an "Upcoming Renewals" panel on the Nautobot home dashboard (Nautobot's plugin system exposes hook points)

**Acceptance:** `nautobot-server runjob nautobot_contract_models.jobs.RenewalCheckJob` produces output. A scheduled-job entry runs it nightly. The dashboard panel surfaces upcoming renewals on the home page.

### Phase 6 — Documentation pass (~half session) — DONE

- ✅ README.md with mapping table, models, REST/GraphQL usage examples,
  install/config/Limitations sections, dev-stack pointer
- ✅ development/README.md updated with the six gotchas hit during the
  build (compose project name, volume permissions, worker-restart for
  jobs.py, jobs-disabled-by-default, makemigrations-uid-mismatch,
  ContentType timing in initial data migrations)
- ✅ docs/ directory with API / GraphQL / Jobs reference docs
  containing curl + jq examples operators can copy-paste
- ✅ Memory entries at
  `~/.claude/projects/-home-rpm-claude-nautobot-nautobot-contract-models/memory/`
  capture every non-obvious gotcha hit during the build (8 feedback
  files + 1 project-state file) so future Nautobot plugins start with
  the lessons baked in

### Phase 7 — Real-world contract modeling (~half session) — DONE

- ✅ Structured SLA fields on Contract: `contract_type`, `coverage_hours`,
  `response_time`, `restoration_time`, `notice_period_days`, `auto_renew`,
  `term_months` (replacing free-text `renewal_terms` with queryable enums)
- ✅ Per-assignment coverage scope on ContractAssignment: `coverage_start`,
  `coverage_end`, `scope_notes`, `is_primary` (supports mid-term changes)
- ✅ Transitive coverage helper in `helpers.py` walking
  `(self, tenant, location, rack, device)` ancestry
- ✅ `RenewalCheckJob` severity rubric considers notice window + auto_renew
- ✅ `CoverageGapJob` + "Coverage Gaps" home dashboard panel
- ✅ 21 integration tests covering helper + Job behavior

### Phase 8 — Cost analytics (~1 session)

**Why:** today's `recurring_cost` field is documented as "periodic, per the
renewal cycle implied by the dates" — ambiguous enough that aggregating
across contracts gives wrong answers. Procurement/finance teams can't get
monthly burn rate, annualized run rate, or 90-day renewal forecast out of
the current schema. Phase 8 normalizes the cost surface and exposes it on
the dashboard.

**Schema change (one migration):**

- `Contract.billing_period` — new ChoiceSet field with values `monthly`,
  `quarterly`, `semiannual`, `annual`, `one_time`
- Migration `0007_contract_billing_period.py` defaults existing rows to
  `monthly` (operators with annual contracts must edit them after upgrade
  — risk acknowledged; alternative was an explicit-blank field that would
  silently render dashboards as "unconfigured" until every contract was
  audited)

**New module `cost.py`:**

- `monthly_cost(contract)` — normalized monthly figure in contract currency
- `annual_cost(contract)` — `monthly_cost × 12`
- `total_contract_value(contract)` — `monthly × term_months + one_time_cost`
- `burn_rate_by_currency(*, on_date=None)` — `dict[currency, Decimal]` for
  active contracts (no FX; we group rather than sum across)
- `renewal_cost_in_window(window_days, *, on_date=None)` — same shape, for
  contracts with `end_date` falling in window
- `spend_by_vendor(*, on_date=None)` — top vendors by current monthly spend

**UI surface:**

- ContractForm + detail panel + list table get `billing_period` and a
  computed `monthly_cost` column
- Two new home dashboard panels:
  - "Cost Summary" — current monthly burn (per currency), annualized,
    top 5 vendors
  - "Renewal Forecast" — total renewal cost in 30/90/365-day windows
    (per currency)

**New Job: `CostReportJob`** — pure read; logs monthly burn + 90-day
forecast + top vendor + coverage-gap count to JobLogEntry. Operators
schedule it weekly to get a trend in JobResult history without us
building a time-series store.

**Tests (~10 new):**

- `test_cost.py` — each billing_period normalization; cross-currency
  grouping; renewal window math; one-time-cost exclusion from burn rate;
  zero/null edge cases
- Extend `test_jobs.py` with CostReportJob

**Acceptance:** dashboard shows correct per-currency burn rate against the
dev seed data; `make test` runs ≥31 tests passing; `nautobot-server
runjob` for CostReportJob produces a JobLogEntry with the expected
INFO-level summary.

### Phase 9 — Renewal Calendar visualization (~1 session) — DONE

A forward-looking, month-by-month renewal heat-map at
`/plugins/contracts/reports/renewal-calendar/`. Operators see "March is
a $400k month for renewals" at a glance and can click through to the
filtered contract list.

- ✅ `cost.renewal_calendar(months=12, on_date=None)` — list of per-month
  dicts with `{year, month, label, totals, contract_count}` grouped by
  currency; window anchors at the first of the current month
- ✅ `ContractRenewalCalendarView` (TemplateView, not NautobotUIViewSet —
  this is a non-CRUD report); URL at the `reports/` prefix to avoid
  collision with the router's `contracts/<uuid>/` detail pattern
- ✅ Calendar template + dedicated CSS (amber single-hue saturation scale,
  not purple — see CLAUDE.md). Real `<table>` semantics, sticky first
  column, horizontal scroll when wide, dark-mode aware via
  `[data-bs-theme="dark"]`, print-friendly, `prefers-reduced-motion`
  honored
- ✅ Click-through cells link to the contract list filtered by
  `end_date__year`, `end_date__month`, `currency`
- ✅ Window selector (3/6/12/24/36 months) — auto-submits on change
- ✅ "Reports" nav group added to the Contracts tab
- ✅ 9 helper tests in `tests/test_calendar.py`

**Migration-default knock-on:** the calendar inherits Phase 8's
billing_period assumption. If existing contracts haven't been re-flagged
(annual contracts still defaulting to monthly), the calendar's per-month
total over-counts proportionally.

## Tech-stack decisions (final, don't relitigate)

| Concern | Choice | Rationale |
|---|---|---|
| Build backend | hatchling | Modern, plays well with uv, no setup.py |
| Dependency manager | uv | Operator preference; fast, reproducible |
| Versioning | CalVer (`YYYY.M.D`) | Communicates "tested against Nautobot version X as of date Y" |
| Linter/formatter | ruff | Single tool, fast, replaces flake8+black+isort |
| Test runner | pytest + pytest-django | Standard for Django/Nautobot |
| Layout | src-layout | `src/nautobot_contract_models/` |
| Author block | `Ryan Malloy <ryan@supported.systems>` | Per the operator's CLAUDE.md |
| License | TBD with operator | Likely Apache-2.0 if intended for community release |

## Anti-patterns to avoid

- **Don't reinvent Tenant/Status/Tag.** Nautobot has these. Use FKs to them.
- **Don't make Contract.devices a real M2M to Device.** Use ContractAssignment with GenericForeignKey so the same model handles Devices, Circuits, VMs, etc. without N tables.
- **Don't write your own ChangeLog.** PrimaryModel gives this for free via the ObjectChange machinery.
- **Don't put business logic in views.** Put it on the model (`Contract.is_expiring_soon()`, `Contract.total_paid()`, etc.) so Job code, API serializers, and templates all see the same answer.
- **Don't ship migrations that aren't `--check`-clean.** First-time integrators will run migrations against existing data; idempotency matters.
- **Don't add CLAUDE.md attribution to commits.** Clean professional messages per the operator's standing rule.

## Validation strategy

- Phase 1: smoke test (plugin imports, dev stack boots)
- Phase 2: pytest + manual `nautobot-server shell` data creation
- Phase 3: manual UI walk-through against the dev stack
- Phase 4: pytest + curl
- Phase 5: cron-trigger the Job, observe the notification fires
- Phase 6: read the docs end to end as if you'd never seen the project

The bingham nautobot at `~/bingham/nautobot/` is a separate Nautobot 3.1 install with real network data populated by `populate_bingham.py` — useful for Phase 5 validation if you want to test against non-synthetic data. Don't modify bingham's stack permanently; install via the dev stack here, then point a *temporary* nautobot-config-shim at bingham's DB if you want to validate against its 57 real Devices.

## Out of scope (v1)

- Multi-currency support (single currency, store as Decimal, document it)
- Approval workflows for contract changes (Nautobot's ApprovalQueue handles general workflows; we don't need contract-specific)
- Document attachments (Nautobot's built-in file/note attachments suffice)
- Reading contracts from external systems (that's an SSoT plugin, not this)
- Per-line-item cost breakdowns (rolls into Invoice; AccountingDimension if anyone asks)
