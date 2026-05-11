# Dev image: Nautobot 3.1 + our plugin (editable install) + nautobot-app-device-lifecycle.
#
# Build context is the repo root (see development/docker-compose.yml). We
# pip install -e /opt/plugin at build time so the editable install metadata
# is registered, then bind-mount the host's src/ over /opt/plugin/src at
# runtime for hot-reload. Restart nautobot-web to pick up code changes.
#
# DLC is installed alongside us so the dev stack exercises the coexistence
# path operators actually run in production. The fix that lets both plugins
# share a Nautobot instance is migration 0009_alter_status_related_name; see
# docs/admin/release_notes/version_2026.5.11.md for the why.

FROM ghcr.io/nautobot/nautobot:3.1-py3.12

USER 0

# Source baked in for the editable install; bind-mount overlays src/ at runtime.
COPY pyproject.toml /opt/plugin/
COPY README.md /opt/plugin/
COPY src /opt/plugin/src
RUN pip install --no-cache-dir -e /opt/plugin

# Coexistence target — see header comment.
RUN pip install --no-cache-dir nautobot-device-lifecycle-mgmt==4.1.2

USER nautobot
