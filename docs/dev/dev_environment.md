# Development Environment

A four-service Docker Compose stack that spins up Postgres + Redis + Nautobot web + Celery worker, with the plugin source bind-mounted as an editable install.

## Prerequisites

- Docker + Docker Compose
- A working Caddy install with the `caddy` external network (see `~/.claude/rules/infrastructure.md` if you're following the operator's standard setup)
- A `contract-models.local` entry in your `/etc/hosts` pointing at the Caddy host

## Bringing the stack up

```shell
cd development/
make build       # First time, or after changing pyproject.toml
make up          # Start the four services
make logs-web    # Tail the web logs
```

The stack is reachable at `https://contract-models.local/`. First boot takes ~60s for migrations + superuser creation. The default credentials are `admin` / `admin` (development only — never use in production).

## Stack layout

| Service | Image | Purpose |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Primary database |
| `redis` | `redis:7-alpine` | Celery broker + cache |
| `nautobot-web` | locally built | uWSGI serving the Nautobot UI |
| `nautobot-worker` | same image | Celery worker for Jobs |

## Editing code

The `src/` directory is bind-mounted into the container as an editable install (`pip install -e .`). Most code changes are picked up by uWSGI's auto-reload:

```shell
make restart     # Restart the web container after structural changes
make restart-worker  # Restart the Celery worker after editing jobs.py
```

**Important:** the worker does NOT auto-reload Job classes. After editing `jobs.py`, restart the worker explicitly or the Job class won't refresh in the registry.

## Common commands

```shell
make shell       # Bash inside the web container
make nbshell     # nautobot-server shell (Python REPL with the ORM loaded)
make test        # Run the integration test suite
make logs        # Tail logs for the whole stack
make down        # Stop containers (data persists in volumes)
make clean       # DESTRUCTIVE — drop all volumes
```

## Tests

```shell
# Integration tests (Django test runner, runs inside the container)
make test

# Just one test module
docker compose exec nautobot-web nautobot-server test --noinput nautobot_contract_models.tests.test_priority

# Lint + format check (host-side, doesn't need the container)
uvx ruff check src/ tests/
uvx ruff format --check src/ tests/
```

## Generating migrations

The dev container runs as `uid=999` (the `nautobot` user inside the image), but your host probably runs as `uid=1000`. `nautobot-server makemigrations` will hit a `PermissionError` writing into the bind-mount — see [Contributing — Migrations](contributing.md#migrations) for the workaround.

## Browsing the API + GraphQL

- REST: `https://contract-models.local/api/plugins/contracts/`
- GraphiQL: `https://contract-models.local/graphql/`
- API docs: `https://contract-models.local/api/docs/`

## Browsing the docs site (when developing docs)

```shell
# From the repo root
uv run --with mkdocs --with mkdocs-material --with mkdocstrings[python] \
       --with mkdocs-glightbox --with markdown-version-annotations \
       mkdocs serve

# Then browse to http://127.0.0.1:8001/
```

The docs site lives at `/docs/` and `mkdocs.yml` at the repo root. The `dev_addr: 127.0.0.1:8001` in `mkdocs.yml` keeps it out of the way of the dev Nautobot stack.

## Tearing down

```shell
make down        # Stop, keep data
make clean       # Stop AND drop volumes (DESTRUCTIVE)
```

## Common gotchas

- **Static media failure banner on the dashboard.** Run `nautobot-server collectstatic --noinput` after adding new CSS files to `src/nautobot_contract_models/static/`.
- **Job not appearing in the registry.** Restart `nautobot-worker`, not just `nautobot-web`. The worker reads the registry on startup.
- **Notes / Changelog / Contacts tabs missing on a new viewset.** They're auto-wired by `NautobotUIViewSetRouter`. If they're missing, your viewset isn't subclassing `NautobotUIViewSet` correctly.
- **URL collision with `<model>/<uuid>/`.** Don't add custom paths under a router-managed prefix. Use a sibling prefix like `reports/` instead.
