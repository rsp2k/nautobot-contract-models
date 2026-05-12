"""Integration tests for the Phase-19 ContractLCM → Contract migration Job.

These tests verify the bridge between DLM's contract model and ours. They
require ``nautobot-app-device-lifecycle-mgmt`` to be installed (it's pinned
into our dev image since commit ``8825616``); on a host environment without
DLM they skip cleanly.

We instantiate the Job class directly with a ``MagicMock`` logger — same
pattern as ``test_jobs.py`` — so the assertions inspect the in-memory
outcome rather than parsing JobLogEntry rows.
"""

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from django.apps import apps as django_apps
from django.contrib.contenttypes.models import ContentType
from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device
from nautobot.extras.models import Status

from nautobot_contract_models.choices import (
    BillingPeriodChoices,
    ContractTypeChoices,
    CoverageHoursChoices,
    ResponseTimeChoices,
)
from nautobot_contract_models.jobs import MigrateContractLCMToContract
from nautobot_contract_models.models import Contract, ContractAssignment, ServiceProvider

from .fixtures import make_device, make_location

DLM_INSTALLED = django_apps.is_installed("nautobot_device_lifecycle_mgmt")


def _ensure_status_for(model, name="Active"):
    """Return a Status named ``name``, extending its content_types to cover ``model``."""
    status, _ = Status.objects.get_or_create(name=name)
    status.content_types.add(ContentType.objects.get_for_model(model))
    return status


def _make_provider_lcm(name="Cisco"):
    """Create a DLM ProviderLCM row. Import is gated so this module loads without DLM."""
    from nautobot_device_lifecycle_mgmt.models import ProviderLCM

    provider, _ = ProviderLCM.objects.get_or_create(name=name)
    return provider


def _make_contract_lcm(
    name="SmartNet 2026",
    provider=None,
    cost=Decimal("500.00"),
    start=None,
    end=None,
    devices=None,
    **kwargs,
):
    """Create a DLM ContractLCM row with safe defaults; attach devices via M2M.

    Returns the saved ContractLCM. Imports are gated so this helper module
    loads even when DLM isn't installed (the test class itself is also gated).
    """
    from nautobot_device_lifecycle_mgmt.models import ContractLCM

    if provider is None:
        provider = _make_provider_lcm()
    if start is None:
        start = date(2026, 1, 1)
    if end is None:
        end = date(2027, 1, 1)
    # ContractLCM.status is a StatusField bound to ContractLCM's ContentType;
    # ensure 'Active' covers it so the assignment succeeds.
    status = _ensure_status_for(ContractLCM)
    lcm = ContractLCM.objects.create(
        name=name,
        provider=provider,
        status=status,
        start=start,
        end=end,
        cost=cost,
        **kwargs,
    )
    if devices:
        lcm.devices.set(devices)
    return lcm


def _run_job(dry_run=False, default_billing_period=BillingPeriodChoices.MONTHLY, strategy="by_name"):
    """Instantiate the Job, mock its logger, run it. Returns (job, result_dict)."""
    job = MigrateContractLCMToContract()
    job.logger = MagicMock()
    result = job.run(
        dry_run=dry_run,
        default_billing_period=default_billing_period,
        provider_match_strategy=strategy,
    )
    return job, result


@unittest.skipUnless(DLM_INSTALLED, "nautobot-app-device-lifecycle-mgmt not installed")
class MigrateContractLCMTests(TestCase):
    """Verify the migration Job's field mapping, idempotency, and dry-run semantics."""

    def test_migrates_basic_fields(self):
        # Pre-create the ServiceProvider name so we exercise the match-by-name path
        # without falling into the create-if-missing branch (covered separately).
        ServiceProvider.objects.create(name="Cisco")
        _ensure_status_for(Contract)
        _make_contract_lcm(name="SmartNet 2026", cost=Decimal("1200.00"))

        _, result = _run_job(dry_run=False)

        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["skipped"], 0)
        contract = Contract.objects.get(name="SmartNet 2026")
        self.assertEqual(contract.provider.name, "Cisco")
        self.assertEqual(contract.recurring_cost, Decimal("1200.00"))
        self.assertEqual(contract.billing_period, BillingPeriodChoices.MONTHLY)
        self.assertEqual(contract.start_date, date(2026, 1, 1))
        self.assertEqual(contract.end_date, date(2027, 1, 1))

    def test_devices_m2m_become_contractassignment(self):
        _ensure_status_for(Contract)
        loc = make_location(name="HQ")
        d1 = make_device(name="dev-01", location=loc)
        d2 = make_device(name="dev-02", location=loc)
        _make_contract_lcm(name="HW Maint", devices=[d1, d2])

        _, result = _run_job(dry_run=False)

        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["assignments"], 2)
        contract = Contract.objects.get(name="HW Maint")
        device_ct = ContentType.objects.get_for_model(Device)
        assignments = ContractAssignment.objects.filter(contract=contract, content_type=device_ct)
        self.assertEqual(assignments.count(), 2)
        self.assertSetEqual({a.object_id for a in assignments}, {d1.pk, d2.pk})

    def test_idempotent_rerun_skips_marked(self):
        _ensure_status_for(Contract)
        _make_contract_lcm(name="Idempotent Test")

        # First run migrates everything.
        _, first_result = _run_job(dry_run=False)
        self.assertEqual(first_result["migrated"], 1)

        # Second run sees the marker custom field and excludes the row entirely.
        _, second_result = _run_job(dry_run=False)
        self.assertEqual(second_result["migrated"], 0)
        self.assertEqual(second_result["skipped"], 0)
        # And we don't create a duplicate Contract.
        self.assertEqual(Contract.objects.filter(name="Idempotent Test").count(), 1)

    def test_dry_run_makes_no_writes(self):
        _ensure_status_for(Contract)
        _make_contract_lcm(name="Dry Run Test")

        _, result = _run_job(dry_run=True)

        # Job reports the would-migrate count but commits nothing.
        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["dry_run"], True)
        self.assertFalse(Contract.objects.filter(name="Dry Run Test").exists())

    def test_provider_create_if_missing(self):
        """The default 'by_name' strategy creates a missing ServiceProvider."""
        _ensure_status_for(Contract)
        _make_contract_lcm(name="New Vendor", provider=_make_provider_lcm("NewProvider"))
        self.assertFalse(ServiceProvider.objects.filter(name="NewProvider").exists())

        _, result = _run_job(dry_run=False, strategy="by_name")

        self.assertEqual(result["migrated"], 1)
        self.assertTrue(ServiceProvider.objects.filter(name="NewProvider").exists())

    def test_provider_strict_skips_unmatched(self):
        """The 'by_name_strict' strategy skips when no ServiceProvider matches."""
        _ensure_status_for(Contract)
        _make_contract_lcm(name="No Match Test", provider=_make_provider_lcm("UnknownVendor"))

        _, result = _run_job(dry_run=False, strategy="by_name_strict")

        self.assertEqual(result["migrated"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertFalse(Contract.objects.filter(name="No Match Test").exists())
        # No provider auto-created in strict mode.
        self.assertFalse(ServiceProvider.objects.filter(name="UnknownVendor").exists())

    def test_default_billing_period_respected(self):
        """The ChoiceVar's billing-period selection lands on the Contract row."""
        ServiceProvider.objects.create(name="Cisco")
        _ensure_status_for(Contract)
        _make_contract_lcm(name="Annual Contract", cost=Decimal("12000.00"))

        _, _ = _run_job(dry_run=False, default_billing_period=BillingPeriodChoices.ANNUAL)

        contract = Contract.objects.get(name="Annual Contract")
        self.assertEqual(contract.billing_period, BillingPeriodChoices.ANNUAL)

    def test_support_level_regex_mapping_best_effort(self):
        """Known support_level strings map to enums; unknowns leave blank + log warning."""
        ServiceProvider.objects.create(name="Cisco")
        _ensure_status_for(Contract)
        _make_contract_lcm(
            name="24x7 Contract",
            support_level="24x7 with 4-hour response",
            contract_type="Hardware Maintenance",
        )
        _make_contract_lcm(
            name="Unmappable Contract",
            support_level="Premium Gold Tier 1",  # Doesn't match any pattern
            contract_type="Custom Tier",
        )

        job, result = _run_job(dry_run=False)

        self.assertEqual(result["migrated"], 2)
        # Mapped contract picked up both axes.
        mapped = Contract.objects.get(name="24x7 Contract")
        self.assertEqual(mapped.coverage_hours, CoverageHoursChoices.HOURS_24X7)
        self.assertEqual(mapped.response_time, ResponseTimeChoices.HOURS_4)
        self.assertEqual(mapped.contract_type, ContractTypeChoices.HARDWARE)
        # Unmapped contract left blank with a logged warning.
        unmapped = Contract.objects.get(name="Unmappable Contract")
        self.assertEqual(unmapped.coverage_hours, "")
        self.assertEqual(unmapped.response_time, "")
        self.assertEqual(unmapped.contract_type, "")
        self.assertGreaterEqual(result["warnings"], 2)
        # Both unmapped axes generated a warning log call.
        warning_calls = [str(c) for c in job.logger.warning.call_args_list]
        self.assertTrue(any("[unmapped]" in c and "support_level" in c for c in warning_calls))
        self.assertTrue(any("[unmapped]" in c and "contract_type" in c for c in warning_calls))
