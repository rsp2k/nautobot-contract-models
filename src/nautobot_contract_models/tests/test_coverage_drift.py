"""Tests for CoverageSnapshot model + Job + drift view — Phase 20."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from django.db import IntegrityError, transaction
from django.urls import reverse
from nautobot.core.testing import TestCase

from nautobot_contract_models.jobs import CoverageSnapshotJob
from nautobot_contract_models.models import CoverageSnapshot

from .fixtures import assign, make_contract, make_device


class CoverageSnapshotModelTests(TestCase):
    """Schema invariants and basic CRUD."""

    def test_unique_constraint_on_date_device(self):
        device = make_device(name="cs-unique")
        today = date.today()
        CoverageSnapshot.objects.create(snapshot_date=today, device=device, was_covered=False)
        # Wrap in an atomic block so the IntegrityError doesn't poison the
        # outer transaction TestCase wraps every test in.
        with self.assertRaises(IntegrityError), transaction.atomic():
            CoverageSnapshot.objects.create(snapshot_date=today, device=device, was_covered=True)


class CoverageSnapshotJobTests(TestCase):
    """Job writes one row per device, idempotent on re-run."""

    def _run_job(self):
        job = CoverageSnapshotJob()
        job.logger = MagicMock()
        return job, job.run()

    def test_job_writes_one_row_per_device(self):
        # Three devices, two covered, one not.
        d1 = make_device(name="cs-cov-1")
        d2 = make_device(name="cs-cov-2")
        d3 = make_device(name="cs-uncov-1")
        contract = make_contract(name="cs-job-contract")
        assign(contract, d1)
        assign(contract, d2)
        _, result = self._run_job()
        self.assertEqual(result["devices_total"], CoverageSnapshot.objects.filter(snapshot_date=date.today()).count())
        self.assertGreaterEqual(result["devices_covered"], 2)
        self.assertGreaterEqual(result["devices_uncovered"], 1)
        # Spot-check one device's row.
        snap = CoverageSnapshot.objects.get(snapshot_date=date.today(), device=d1)
        self.assertTrue(snap.was_covered)
        snap_uncov = CoverageSnapshot.objects.get(snapshot_date=date.today(), device=d3)
        self.assertFalse(snap_uncov.was_covered)

    def test_idempotent_rerun_same_day(self):
        make_device(name="cs-idem-1")
        self._run_job()
        count_after_first = CoverageSnapshot.objects.filter(snapshot_date=date.today()).count()
        self._run_job()
        count_after_second = CoverageSnapshot.objects.filter(snapshot_date=date.today()).count()
        self.assertEqual(count_after_first, count_after_second)


class CoverageDriftViewTests(TestCase):
    """The /reports/coverage-drift/ page."""

    url = reverse("plugins:nautobot_contract_models:contract_coverage_drift")
    user_permissions = ("nautobot_contract_models.view_contract",)

    def test_empty_history_shows_instructional_alert(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("No snapshot history", body)

    def test_lost_coverage_row_appears(self):
        # Simulate: 30 days ago the device was covered; today it isn't.
        device = make_device(name="cs-drift-lost")
        old_date = date.today() - timedelta(days=30)
        CoverageSnapshot.objects.create(snapshot_date=old_date, device=device, was_covered=True)
        CoverageSnapshot.objects.create(snapshot_date=date.today(), device=device, was_covered=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("cs-drift-lost", body)
        # The "Lost coverage" header should be present and the device row in its section.
        self.assertIn("Lost coverage", body)

    def test_newly_covered_row_appears(self):
        device = make_device(name="cs-drift-new")
        old_date = date.today() - timedelta(days=30)
        CoverageSnapshot.objects.create(snapshot_date=old_date, device=device, was_covered=False)
        CoverageSnapshot.objects.create(snapshot_date=date.today(), device=device, was_covered=True)
        response = self.client.get(self.url)
        body = response.content.decode("utf-8")
        self.assertIn("cs-drift-new", body)
        self.assertIn("Newly covered", body)

    def test_new_device_not_in_baseline_skipped(self):
        # Device exists only in today's snapshot — should NOT appear as drift
        # (no baseline state to compare against).
        baseline_dev = make_device(name="cs-baseline")
        new_dev = make_device(name="cs-brand-new")
        old_date = date.today() - timedelta(days=30)
        CoverageSnapshot.objects.create(snapshot_date=old_date, device=baseline_dev, was_covered=True)
        CoverageSnapshot.objects.create(snapshot_date=date.today(), device=baseline_dev, was_covered=True)
        CoverageSnapshot.objects.create(snapshot_date=date.today(), device=new_dev, was_covered=True)
        response = self.client.get(self.url)
        body = response.content.decode("utf-8")
        # The brand-new device should not appear in either drift section.
        self.assertNotIn("cs-brand-new", body)
