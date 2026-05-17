"""Nautobot config for the contract-models dev stack.

Loaded via volume mount at /opt/nautobot/nautobot_config.py inside each
Nautobot container. Imports the upstream defaults, then overrides only what
we need: PLUGINS, PLUGINS_CONFIG, and a couple of dev toggles.
"""

import os

# Pull in Nautobot's default settings (DB / cache / Celery wiring from env vars).
from nautobot.core.settings import *  # noqa: F401,F403
from nautobot.core.settings_funcs import is_truthy  # noqa: F401

DEBUG = is_truthy(os.environ.get("NAUTOBOT_DEBUG", "true"))

# Append the Nautobot test client's default Host header so `self.client.get(...)`
# in unit tests doesn't get bounced as Bad Request by ALLOWED_HOSTS. The base
# NAUTOBOT_ALLOWED_HOSTS comes from the env var (production hostnames); the test
# client uses "nautobot.example.com" per NautobotTestClient.__init__. Without
# this, every self.client.get hits a 400. Safe to leave in production configs:
# the example.com TLD is reserved (RFC 2606), so no real host can match it.
ALLOWED_HOSTS = list(globals().get("ALLOWED_HOSTS", [])) + ["nautobot.example.com"]

PLUGINS = [
    "nautobot_contract_models",
    # DLC is installed alongside us in the dev stack so we exercise the
    # coexistence path real operators run. Phase 18 (migration 0009) makes
    # this work without a Status reverse-accessor collision.
    "nautobot_device_lifecycle_mgmt",
]

PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        # Renewal-alert window for the Phase-5 Job. Contracts whose end_date
        # falls within this many days from "now" surface in the alert.
        "renewal_window_days": int(os.environ.get("CONTRACT_RENEWAL_WINDOW_DAYS", "60")),
        # Phase 19: surgically remove DLM's Contracts nav group at startup so
        # the dev stack exercises the "one canonical Contracts surface" UX.
        # Toggleable via env var without editing this file for easy demo flipping.
        "hide_dlm_contracts_nav": is_truthy(os.environ.get("HIDE_DLM_CONTRACTS_NAV", "true")),
    },
    # nautobot_device_lifecycle_mgmt uses sane defaults; no overrides needed
    # for dev work. Add a sub-dict here if you start exercising its config.
}
