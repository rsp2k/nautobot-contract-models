"""Stub heavy framework imports so unit tests can run without Nautobot installed.

The package's ``__init__.py`` imports ``nautobot.apps.NautobotAppConfig`` at
top level, which transitively pulls in Django + the entire Nautobot install.
Schema and import-shape tests don't need any of that — they just need the
package to be *importable*.

This conftest installs lightweight ``MagicMock`` placeholders for every
external module our package imports, *before* pytest discovers the package.
``setdefault`` preserves real modules when they happen to be installed (CI
with the full stack), and fills in mocks otherwise (local dev / sdist
verification).

Tests that need real Django machinery should live in ``tests/integration/``
and run inside the dev container via ``make test``.
"""

import sys
from unittest.mock import MagicMock

_FAKE_MODULES = [
    "nautobot",
    "nautobot.apps",
    "nautobot.apps.api",
    "nautobot.apps.filters",
    "nautobot.apps.forms",
    "nautobot.apps.jobs",
    "nautobot.apps.tables",
    "nautobot.apps.ui",
    "nautobot.apps.urls",
    "nautobot.apps.views",
    "nautobot.core",
    "nautobot.core.models",
    "nautobot.core.models.generics",
    "nautobot.core.views",
    "nautobot.core.views.generic",
    "nautobot.dcim",
    "nautobot.dcim.models",
    "nautobot.extras",
    "nautobot.extras.choices",
    "nautobot.extras.models",
    "nautobot.extras.models.statuses",
    "nautobot.extras.utils",
    "nautobot.tenancy",
    "nautobot.tenancy.models",
    "django",
    "django.conf",
    "django.core",
    "django.core.exceptions",
    "django.contrib",
    "django.contrib.contenttypes",
    "django.contrib.contenttypes.fields",
    "django.contrib.contenttypes.models",
    "django.db",
    "django.db.models",
    "django_tables2",
]

for name in _FAKE_MODULES:
    sys.modules.setdefault(name, MagicMock())
