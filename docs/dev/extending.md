# Extending the App

This page documents the extension points — how to add new fields, new models, new helpers, or new report views without breaking existing behavior.

## Adding a new field to `Contract`

1. Edit `src/nautobot_contract_models/models/contract.py` and add the field
2. Generate a migration with `nautobot-server makemigrations nautobot_contract_models` (or hand-write it if you hit the UID-mismatch issue)
3. Add the field to `forms/contract.py` (`ContractForm.Meta.fields`) so the form picks it up
4. If the field uses choices, define a `ChoiceSet` in `choices.py` and reference it
5. Add a column to `tables/contract.py` if it should appear in the list view
6. Add it to `filters/contract.py` `Meta.fields` so the FilterSet picks it up (this also makes it available via the REST API)
7. The detail view uses `ObjectFieldsPanel(fields="__all__")` so the field appears automatically
8. The CSV import surface is auto-generated from the serializer — no extra wiring needed
9. Add a test exercising any new behavior

## Adding a new model

1. Create `src/nautobot_contract_models/models/<name>.py` subclassing `BaseModel` (telemetry / write-once data) or `PrimaryModel` (UI-managed with ChangeLog / Tags / Relationships)
2. Add `@extras_features(...)` for the features the model needs (`graphql`, `webhooks`, `custom_fields`, etc.)
3. Add it to `models/__init__.py`'s import list and `__all__`
4. Generate the migration
5. If the model needs a UI, add a viewset to `views/<name>.py` — subclass `NautobotUIViewSet` for full CRUD or `TemplateView` for non-CRUD reports
6. Wire URLs in `urls.py` — use `router.register(...)` for CRUD or `path(...)` under a sibling prefix like `reports/`
7. Add a serializer + filter set + API viewset (the read-only `CostSnapshot` setup is a good reference)
8. Add to the navigation menu in `navigation.py`

## Adding a new helper

The plugin separates helpers by concern:

- `cost.py` — anything about money (burn rate, renewal forecast, snapshots)
- `priority.py` — action-priority rubric (URGENT / WARNING / INFO)
- `helpers.py` — cross-cutting queries (transitive coverage, etc.)

Add to whichever file matches the concern; create a new file if the concern is genuinely new. Tests live in the matching `tests/test_<name>.py` file.

## Adding a new dashboard panel

1. Write the data callable in `homepage.py` — receives `request`, returns a value (or dict for multiple values)
2. Create the template under `templates/nautobot_contract_models/inc/<name>_panel.html`
3. Append a `HomePagePanel(...)` to the `layout` tuple in `homepage.py`
4. Set `weight` to position the panel — lower number = higher in the column

The Cost Summary panel is a good reference for panels with multiple sub-values; the Coverage Gaps panel for simple single-value panels.

## Adding a new report page (non-CRUD view)

1. Create `views/<name>.py` with a `TemplateView` subclass guarded by `PermissionRequiredMixin`
2. Create the template under `templates/nautobot_contract_models/<name>.html` — extend `base.html` and use `{% load static %}` + `{% static '<path>' %}` for any static assets
3. Add a CSS file under `static/nautobot_contract_models/<name>.css` if styling is needed
4. Wire the URL in `urls.py` under the `reports/` prefix (NOT under `contracts/` — the router's UUID-detail pattern collides)
5. Add a `NavMenuItem` to the "Reports" group in `navigation.py`
6. Run `collectstatic` after adding CSS

The Renewal Calendar (`views/calendar.py`), Action Required (`views/action_required.py`), and Cost History (`views/cost_history.py`) are three reference implementations.

## Adding a new Job

1. Edit `jobs.py` — subclass `Job`, define vars, implement `run(...)`
2. Add the class to `register_jobs(...)` at the bottom of the file
3. **Restart the worker** (`make restart-worker` or `docker compose restart nautobot-worker`) — the registry only refreshes on worker startup
4. Visit `/jobs/?grouping=Contracts` — newly-discovered Jobs are disabled by default; toggle Enabled

Test the Job by mocking `self.logger` and calling `.run(...)` directly — `tests/test_jobs.py` has examples. Don't bother running it through `run_job_for_testing` unless you need the JobResult / scheduling integration.

## Where things live (cheat sheet)

| File | Purpose |
|---|---|
| `models/*.py` | Django ORM models |
| `migrations/*.py` | Schema migrations (auto-generated where possible) |
| `choices.py` | ChoiceSet enumerations |
| `forms/*.py` | NautobotModelForm + filter forms |
| `tables/*.py` | django_tables2 list-view tables |
| `filters/*.py` | django-filter filtersets (used by both UI list views AND REST API) |
| `views/*.py` | UI viewsets (CRUD via `NautobotUIViewSet`) and report views (TemplateView) |
| `api/serializers.py` | DRF serializers |
| `api/views.py` | API viewsets (`NautobotModelViewSet` for CRUD, mixin composition for read-only) |
| `api/urls.py` | API URL registration |
| `urls.py` | UI URL registration (router + manual `path()` for reports) |
| `navigation.py` | Left sidebar menu |
| `homepage.py` | Home dashboard panels |
| `cost.py` | Cost / burn / renewal / snapshot helpers |
| `priority.py` | Action-priority rubric |
| `helpers.py` | Transitive coverage + other cross-cutting queries |
| `jobs.py` | Background Jobs |
| `templates/nautobot_contract_models/*.html` | Page templates |
| `templates/nautobot_contract_models/inc/*.html` | Panel includes |
| `static/nautobot_contract_models/*.css` | Stylesheets |
| `tests/*.py` | Integration tests (Django test runner) |
