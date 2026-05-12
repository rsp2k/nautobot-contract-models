"""Nautobot content plugin: first-class Contract / Invoice / ServiceProvider models."""

from importlib.metadata import PackageNotFoundError, version

from nautobot.apps import NautobotAppConfig

try:
    __version__ = version("nautobot-contract-models")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"


def _maybe_hide_dlm_contracts_nav():
    """Surgically remove DLM's ``Contracts`` nav group when the operator opts in.

    Gated on ``PLUGINS_CONFIG['nautobot_contract_models']['hide_dlm_contracts_nav']``.
    Only fires when ``nautobot-app-device-lifecycle-mgmt`` is also installed —
    skips silently otherwise. Preserves DLM's ``Hardware Notices``,
    ``Software Lifecycle``, and ``Reports`` groups intact.

    This pokes at the private ``registry["nav_menu"]`` dict (Nautobot has no
    public "hide sibling plugin's nav" hook). The right long-term answer is an
    upstream PR to DLM adding a ``DISABLE_CONTRACTS_SURFACE`` PLUGINS_CONFIG
    flag — until then, this stays opt-in (default False) and behind an explicit
    operator setting so nothing happens by accident.
    """
    from django.apps import apps as django_apps
    from django.conf import settings

    cfg = settings.PLUGINS_CONFIG.get("nautobot_contract_models", {})
    if not cfg.get("hide_dlm_contracts_nav", False):
        return
    if not django_apps.is_installed("nautobot_device_lifecycle_mgmt"):
        # Flag was set but DLM isn't installed — no-op, no error.
        return

    try:
        from nautobot.core.apps import registry
    except ImportError:
        return

    dlm_tab = registry.get("nav_menu", {}).get("tabs", {}).get("Device Lifecycle")
    if dlm_tab is None:
        return
    dlm_tab.get("groups", {}).pop("Contracts", None)


class NautobotContractModelsConfig(NautobotAppConfig):
    """App configuration for the contract-models plugin."""

    name = "nautobot_contract_models"
    verbose_name = "Nautobot Contract Models"
    description = "First-class Contract, Invoice, and ServiceProvider models for Nautobot."
    version = __version__
    author = "Ryan Malloy"
    author_email = "ryan@supported.systems"
    base_url = "contracts"
    required_settings: list[str] = []
    default_settings: dict = {
        # Days-out window for the renewal-alert Job (Phase 5).
        "renewal_window_days": 60,
        # When True AND nautobot-app-device-lifecycle-mgmt is installed, our
        # AppConfig.ready() removes DLM's "Contracts" nav group at startup.
        # See `_maybe_hide_dlm_contracts_nav` above for the rationale.
        "hide_dlm_contracts_nav": False,
    }
    caching_config: dict = {}

    def ready(self):
        """Wire the lazy DLM-nav-hide hook on ``request_started`` so it fires after every plugin's ready().

        We can't call ``_maybe_hide_dlm_contracts_nav`` directly from ready()
        because plugins load in INSTALLED_APPS order — if our app comes before
        DLM in the operator's PLUGINS list, DLM's nav isn't in the registry
        yet when our ready() runs. Deferring via ``request_started`` ensures
        the hook fires only after every app's ready() has completed (the first
        HTTP request can't be handled until then). One-shot via dispatch_uid +
        an in-state flag so it only runs once per process.
        """
        super().ready()

        from django.core.signals import request_started

        state = {"hidden": False}

        def _hide_on_first_request(*args, **kwargs):
            if state["hidden"]:
                return
            state["hidden"] = True
            _maybe_hide_dlm_contracts_nav()

        request_started.connect(
            _hide_on_first_request,
            weak=False,
            dispatch_uid="nautobot_contract_models.hide_dlm_contracts_nav",
        )


config = NautobotContractModelsConfig
