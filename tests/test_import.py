"""Smoke test: the package imports cleanly under the conftest's Nautobot mocks.

Deeper assertions on the AppConfig (e.g. ``config.name`` resolving to the
expected string, the default settings being correctly populated) require the
*real* Nautobot AppConfig metaclass — its descriptor machinery doesn't survive
being subclassed off a MagicMock. Those tests live in ``tests/integration/``
and run inside the dev container via ``make test``.
"""


def test_package_imports():
    import nautobot_contract_models

    assert hasattr(nautobot_contract_models, "config")
    assert hasattr(nautobot_contract_models, "__version__")


def test_subpackages_importable():
    """Each empty Phase-1 subpackage should be importable as well."""
    import nautobot_contract_models.api  # noqa: F401
    import nautobot_contract_models.filters  # noqa: F401
    import nautobot_contract_models.forms  # noqa: F401
    import nautobot_contract_models.models  # noqa: F401
    import nautobot_contract_models.tables  # noqa: F401
    import nautobot_contract_models.views  # noqa: F401
