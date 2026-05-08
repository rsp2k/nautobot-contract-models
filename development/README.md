# Dev Stack

Self-contained Nautobot 3.1 + the contract-models plugin, isolated from any other Nautobot you might have running on this host.

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
make restart        # restarts nautobot-web; worker picks up new imports too
```

The plugin `src/` is bind-mounted into the container, so file edits are immediately visible — but Python's import cache means a process restart is required.

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

### 2. Volume permissions on first boot

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

## Tear down

```bash
make down       # stop containers, keep data
make clean      # destroy volumes (postgres, media, etc.)
```
