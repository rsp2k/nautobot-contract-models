# Dev Stack

Self-contained Nautobot 3.1 + the contract-models plugin **+ `nautobot-app-device-lifecycle`**, isolated from any other Nautobot you might have running on this host.

> **Why DLC is here:** the dev stack mirrors how operators actually run us in production — alongside DLC. The two plugins both define a `Contract*` model, and without our Phase 18 fix (`migration 0009_alter_status_related_name`) they'd clash on Django's `Status.contracts` reverse accessor and prevent Nautobot from booting. Pinning DLC into the dev image means any future regression of that fix breaks our dev stack loudly instead of silently shipping. See `docs/admin/release_notes/version_2026.5.11.md` for the full backstory.

## Prerequisites

- Docker + Docker Compose
- An external Docker network named `caddy` running `caddy-docker-proxy` (per `~/.claude/CLAUDE.md`'s caddy convention). If you don't have one yet:
  ```bash
  docker network create caddy
  ```
  Then run a `caddy-docker-proxy` container attached to it.

## Bootstrap

```bash
cd development/
cp .env.example .env
$EDITOR .env                           # set passwords + DOMAIN
make build && make up
make logs-web                          # wait for "running on http://..." (~60s first boot)
```

Open `https://<DOMAIN>/` (e.g. `https://contract-models.local/`) and log in with `NAUTOBOT_SUPERUSER_NAME` / `NAUTOBOT_SUPERUSER_PASSWORD`.

> Add `127.0.0.1 contract-models.local` to `/etc/hosts` if you're using the default `.local` domain and your Caddy config doesn't already resolve it.

## After editing plugin code

```bash
make restart        # restarts nautobot-web only
```

The plugin `src/` is bind-mounted into the container, so file edits are immediately visible — but Python's import cache means a process restart is required.

⚠️ **If you edit `jobs.py`, restart the worker too:**

```bash
docker compose restart nautobot-web nautobot-worker
```

Celery workers run in their own process and have their own Python state. Restarting just `nautobot-web` is not enough — running the Job will produce `KeyError: Job class not found for class path nautobot_contract_models.jobs.RenewalCheckJob` until the worker is also restarted.

## Run the test suite (inside the container)

```bash
make test           # runs `nautobot-server test nautobot_contract_models`
```

Lighter-weight schema/import tests run on the host with `uv run pytest` (uses the conftest.py mocking pattern).

## Gotchas — same as the companion plugin

These are the not-obvious failures the operator hit on the SSoT-Hudu plugin's first bringup. They apply identically here.

### 1. `COMPOSE_PROJECT_NAME`, not `COMPOSE_PROJECT`

The `.env` *must* set `COMPOSE_PROJECT_NAME=nautobot-contract-models` (the canonical docker-compose env var), not `COMPOSE_PROJECT`. The latter is only a YAML substitution variable — it renames containers but does **not** tell docker-compose what the project itself is called.

Without `COMPOSE_PROJECT_NAME`, docker-compose falls back to the directory name as the project. Our directory is `development/`, which collides with at least one other project on this host. Symptom: postgres data volume gets shared across projects, password mismatch, "FATAL: password authentication failed for user nautobot" on every web boot.

`docker compose ls -a` is the truth and shows the collision clearly.

### 2. Worker restart is separate from web restart

See the "After editing plugin code" section above. The worker container has its own Python interpreter and class registry — `nautobot-server runjob` from the UI talks to Celery, which uses the worker's Python state, not the web container's.

`make restart` (which runs `docker compose restart nautobot-web`) is not enough when you edit `jobs.py`. Use `docker compose restart nautobot-web nautobot-worker` or extend the Makefile.

### 3. Volume permissions on first boot

Nautobot runs as uid 999 inside the container; docker-named-volumes start as root-owned (uid 0). Result: `PermissionError: [Errno 13] Permission denied: '/opt/nautobot/media/devicetype-images'` during `_preprocess_settings` on first boot.

Fix once at install time:

```bash
docker compose down
docker run --rm \
  -v nautobot-contract-models_nautobot-media:/m \
  -v nautobot-contract-models_nautobot-static:/s \
  -v nautobot-contract-models_nautobot-git-repos:/g \
  alpine sh -c 'chown -R 999:999 /m /s /g'
docker compose up -d
```

### 4. Newly-discovered Jobs are disabled by default

Nautobot 3.x ships every plugin Job in the `disabled` state. Operators must explicitly enable Jobs from the UI before the Run button works:

```bash
# Option A: enable from the shell
docker compose exec nautobot-web nautobot-server shell -c "
from nautobot.extras.models import Job
Job.objects.filter(name='Check upcoming renewals').update(enabled=True)
"

# Option B: enable from the UI
# Apps → Jobs → "Check upcoming renewals" → Edit → check Enabled → Save
```

This is intentional Nautobot security — operators opt-in to running plugin code. In production, document the enable step in your install runbook rather than working around it.

### 5. Bind-mount permissions when running `makemigrations`

The host's `src/` is owned by your user (uid 1000). The container runs as `nautobot` (uid 999). When `makemigrations` writes a new migration file, it can't write to the bind mount.

Workaround: run as root in the container, then chown back to your host UID:

```bash
docker compose exec -u 0 nautobot-web nautobot-server makemigrations nautobot_contract_models
docker compose exec -u 0 nautobot-web sh -c 'chown -R 1000:1000 /opt/plugin/src/nautobot_contract_models/migrations/'
```

### 6. Initial-install data migrations and ContentTypes

If you write a `0002_*` data migration that needs to bind data (Status, Role, etc.) to ContentTypes for models the same `migrate` run has just created, you'll hit `ContentType.DoesNotExist` — `post_migrate` (which lazily creates ContentType rows) fires only after the entire `migrate` command completes.

The fix: force-create them at the top of the migration's RunPython function. See `migrations/0002_register_statuses.py` for the exact pattern.

## Tear down

```bash
make down       # stop containers, keep data
make clean      # destroy volumes (postgres, media, etc.)
```
