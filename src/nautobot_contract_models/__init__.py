"""Nautobot content plugin: first-class Contract / Invoice / ServiceProvider models."""

from importlib.metadata import PackageNotFoundError, version

from nautobot.apps import NautobotAppConfig

try:
    __version__ = version("nautobot-contract-models")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"


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
    }
    caching_config: dict = {}


config = NautobotContractModelsConfig
