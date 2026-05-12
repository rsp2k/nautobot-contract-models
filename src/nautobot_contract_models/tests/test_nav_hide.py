"""Tests for the Phase-19 opt-in DLM Contracts nav-hide hook.

The hook (``_maybe_hide_dlm_contracts_nav`` in ``__init__.py``) is fired from
``NautobotContractModelsConfig.ready()``. It modifies the global Nautobot
nav registry, which is a module-level singleton. We snapshot the registry
in ``setUp`` and restore in ``tearDown`` so tests can re-enter ``ready()``
behavior without polluting cross-test state.

The first three tests are gated on DLM being installed — they verify
surgical removal of the Contracts group while preserving siblings. The
fourth test runs unconditionally and uses ``patch.object`` on Django's
apps registry to simulate "DLM is reported absent", confirming the hook
is a no-op rather than raising.
"""

import copy
import unittest
from unittest.mock import patch

from django.apps import apps as django_apps
from django.test import override_settings
from nautobot.core.testing import TestCase

from nautobot_contract_models import _maybe_hide_dlm_contracts_nav

DLM_INSTALLED = django_apps.is_installed("nautobot_device_lifecycle_mgmt")


class _NavRegistrySnapshotMixin:
    """Save/restore the nav_menu sub-tree of Nautobot's global registry per test."""

    def setUp(self):
        super().setUp()
        from nautobot.core.apps import registry

        self._registry = registry
        self._nav_snapshot = copy.deepcopy(registry.get("nav_menu", {}))

    def tearDown(self):
        # Nautobot's Store rejects `__setitem__` overwrites — we can't just
        # re-assign the snapshot. Mutate the underlying dict in place: clear it,
        # then re-populate from the snapshot. This goes through __getitem__
        # (allowed) and dict.clear/update (operates on the returned dict directly).
        nav = self._registry["nav_menu"]
        nav.clear()
        nav.update(self._nav_snapshot)
        super().tearDown()


@unittest.skipUnless(DLM_INSTALLED, "nautobot-app-device-lifecycle-mgmt not installed")
class HideDLMContractsNavTests(_NavRegistrySnapshotMixin, TestCase):
    """Verify the hook surgically removes DLM's Contracts group when the operator opts in."""

    def test_flag_default_false_keeps_dlm_nav(self):
        """No flag → DLM's Contracts group remains untouched."""
        with override_settings(PLUGINS_CONFIG={"nautobot_contract_models": {}}):
            _maybe_hide_dlm_contracts_nav()
        dlm_tab = self._registry["nav_menu"]["tabs"].get("Device Lifecycle", {})
        self.assertIn(
            "Contracts",
            dlm_tab.get("groups", {}),
            "DLM's Contracts group should still be present when flag is not set",
        )

    def test_flag_true_removes_dlm_contracts_group(self):
        """Flag set → DLM's Contracts group is removed."""
        with override_settings(PLUGINS_CONFIG={"nautobot_contract_models": {"hide_dlm_contracts_nav": True}}):
            _maybe_hide_dlm_contracts_nav()
        dlm_tab = self._registry["nav_menu"]["tabs"].get("Device Lifecycle", {})
        self.assertNotIn(
            "Contracts",
            dlm_tab.get("groups", {}),
            "DLM's Contracts group should have been removed when flag is True",
        )

    def test_flag_true_preserves_other_dlm_groups(self):
        """Flag set → only Contracts goes; sibling groups (Hardware Notices etc.) stay."""
        # Snapshot the names of DLM's groups BEFORE we run the hook, so the
        # assertion stays robust across DLM minor-version renames.
        dlm_tab = self._registry["nav_menu"]["tabs"].get("Device Lifecycle", {})
        groups_before = set(dlm_tab.get("groups", {}).keys())
        self.assertIn("Contracts", groups_before, "Test precondition: DLM Contracts group present")
        non_contracts_before = groups_before - {"Contracts"}
        self.assertGreater(
            len(non_contracts_before),
            0,
            "Test precondition: DLM has at least one non-Contracts group",
        )

        with override_settings(PLUGINS_CONFIG={"nautobot_contract_models": {"hide_dlm_contracts_nav": True}}):
            _maybe_hide_dlm_contracts_nav()

        groups_after = set(self._registry["nav_menu"]["tabs"]["Device Lifecycle"].get("groups", {}).keys())
        self.assertEqual(
            groups_after,
            non_contracts_before,
            "All non-Contracts DLM groups should survive the surgical hide",
        )


class HideDLMContractsNavNoopTests(_NavRegistrySnapshotMixin, TestCase):
    """The hook is a no-op (no errors) when DLM is reported absent — regardless of the flag."""

    def test_flag_true_dlm_not_installed_is_noop(self):
        """Flag set but DLM reported absent → silent no-op."""
        with patch.object(django_apps, "is_installed", return_value=False):
            with override_settings(PLUGINS_CONFIG={"nautobot_contract_models": {"hide_dlm_contracts_nav": True}}):
                try:
                    _maybe_hide_dlm_contracts_nav()
                except Exception as exc:  # pragma: no cover (regression guard)
                    self.fail(f"Hook raised unexpectedly when DLM absent: {exc}")
