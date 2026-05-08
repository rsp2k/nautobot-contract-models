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

PLUGINS = [
    "nautobot_contract_models",
]

PLUGINS_CONFIG = {
    "nautobot_contract_models": {
        # Renewal-alert window for the Phase-5 Job. Contracts whose end_date
        # falls within this many days from "now" surface in the alert.
        "renewal_window_days": int(os.environ.get("CONTRACT_RENEWAL_WINDOW_DAYS", "60")),
    },
}
