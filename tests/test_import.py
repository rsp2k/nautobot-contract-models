"""Smoke test: the package imports cleanly under the conftest's Nautobot mocks.

Why this is the *only* thing tested at the host-pytest level:

The conftest installs ``MagicMock`` placeholders for the entire ``nautobot.*``
import chain so that the package can be imported without a real Nautobot
install. Top-level import works fine — the package's ``__init__.py`` only
references ``NautobotAppConfig``, which doesn't get instantiated at import
time.

But anything deeper — eagerly importing forms / tables / filters / views —
hits Python's metaclass machinery: each class in the plugin inherits from
multiple mocked base classes (``StatusModelFilterSetMixin``,
``TenancyModelFilterSetMixin``, ``NautobotFilterSet``…), and each MagicMock
attribute has its own auto-generated metaclass with no common ancestor.
Python raises ``TypeError: metaclass conflict``.

The lesson (recorded in the project's memory file): host-pytest is only
useful for top-level import smoke. Anything that exercises class hierarchies
must run inside the dev container via ``make test``, where the real Nautobot
metaclasses are loaded before pytest collection begins.
"""


def test_package_imports():
    import nautobot_contract_models

    assert hasattr(nautobot_contract_models, "config")
    assert hasattr(nautobot_contract_models, "__version__")
