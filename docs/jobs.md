# Jobs reference

The plugin currently exposes one Job:

## RenewalCheckJob — "Check upcoming renewals"

**Group:** Contracts
**Path:** `nautobot_contract_models.jobs.RenewalCheckJob`
**Read-only:** yes — does not modify any contracts
**Sensitive variables:** no — schedulable

### What it does

Walks contracts whose `end_date` falls within `window_days` from today. For each match, writes a `JobLogEntry` with the Contract attached as `extra={"object": ...}` so the entry shows up as a clickable link in the Job result UI.

Log levels:
- `WARNING` — contracts expiring within 7 days
- `INFO` — contracts expiring later in the window

The Job returns the count of contracts reported, which surfaces as the JobResult's "Result" field for at-a-glance review.

### Inputs

| Variable | Type | Default | Description |
|---|---|---|---|
| `window_days` | IntegerVar (1-3650) | `PLUGINS_CONFIG.renewal_window_days` (default 60) | Days from today to look ahead |
| `include_expired` | BooleanVar | `False` | Include contracts whose `end_date` has already passed |

### Running

#### From the UI

**Apps → Jobs → "Check upcoming renewals"** → Run.

> ⚠️ The Job ships **disabled** (Nautobot 3.x default for newly-discovered Jobs). Enable it once at install time:
> Apps → Jobs → "Check upcoming renewals" → Edit → check Enabled → Save.

#### From the CLI

```bash
nautobot-server runjob "Contracts.RenewalCheckJob" --data '{"window_days": 30, "include_expired": false}'
```

#### From the API

```bash
curl -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -X POST "https://nautobot.example.com/api/extras/jobs/<job-uuid>/run/" \
  -d '{"data": {"window_days": 30, "include_expired": false}}'
```

#### Scheduled

**Apps → Jobs → Scheduled Jobs → Add**. Cron-style or interval scheduling. The Job is `has_sensitive_variables = False`, so the schedule UI is fully available.

### Output

A typical run produces:

```
[INFO] initialization | Check upcoming renewals | Running job
[INFO] run | Acme Master Services Agreement | Contract 'Acme Master Services Agreement' (provider=Acme Networks) expires 2026-05-30 — 21 day(s) remaining.
[INFO] run | (no object) | Renewal check complete: 1 contract(s) within 60-day window.
[SUCCESS] post_run | (no object) | Job completed
```

The "Object" column for per-contract entries links back to the Contract detail page.

### Routing notifications

The Job is intentionally read-only — it does not send notifications directly. To route warnings into Slack / email / PagerDuty:

1. **Apps → Webhooks** → Add
2. Set the trigger to `JobLogEntry` create
3. Filter on `log_level=warning` and the Job's UUID
4. Configure your destination (Slack incoming webhook, etc.)

This separation is deliberate: it lets operators choose any notification stack, and the Job's responsibility stays focused on identifying the renewals.

### Examples of useful schedules

| Schedule | Use case |
|---|---|
| Daily at 9am | Nightly renewals report into a #contracts channel |
| Weekly Mondays | Procurement-team weekly digest |
| Monthly 1st | Monthly board-prep snapshot of upcoming costs |

For per-team windows, configure separate scheduled jobs with different `window_days` values.

## Adding more Jobs

To extend the plugin with additional Jobs, add classes to `src/nautobot_contract_models/jobs.py` and call `register_jobs(YourJob)` at module load. Then restart the worker:

```bash
docker compose restart nautobot-web nautobot-worker
```

Both restarts are required — `nautobot-web` re-syncs the `Job` model rows in the DB; `nautobot-worker` reloads the Python class registry.
