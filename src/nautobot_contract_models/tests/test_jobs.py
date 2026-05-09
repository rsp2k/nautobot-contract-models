"""Integration tests for RenewalCheckJob severity rubric and CoverageGapJob.

We instantiate the Job classes directly and patch ``self.logger`` rather than
running them through ``run_job_for_testing``. Why:

- The severity rubric is a per-contract decision (which logger level is
  called) — directly inspecting ``logger.warning.call_args_list`` is cleaner
  than parsing JobLogEntry rows.
- The Jobs themselves are pure functions of their queryset; we don't need
  the JobResult / scheduling machinery wrapped around them.

Tests where we *do* care about that machinery (e.g., scheduling, sensitive
variables, the Job appearing in the UI) run as Playwright smoke tests
during phase-bringup, not in this suite.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

from nautobot.core.testing import TestCase

from nautobot_contract_models.jobs import CoverageGapJob, RenewalCheckJob

from .fixtures import assign, make_contract, make_device, make_location, make_tenant


class RenewalCheckJobSeverityTests(TestCase):
    """Verify the per-contract severity rubric in RenewalCheckJob.run()."""

    def _instantiate_job(self):
        job = RenewalCheckJob()
        job.logger = MagicMock()
        return job

    def test_far_future_contract_logged_at_info(self):
        # Ends 90 days out, no notice period — informational only.
        make_contract(
            name="Distant Renewal",
            end_date=date.today() + timedelta(days=90),
        )
        job = self._instantiate_job()

        count = job.run(window_days=180, include_expired=False)

        self.assertEqual(count, 1)
        # Per-contract line at INFO; rubric did not escalate to WARNING.
        # (The summary line at the end is also INFO — at least one INFO call.)
        self.assertGreaterEqual(job.logger.info.call_count, 1)
        self.assertEqual(job.logger.warning.call_count, 0)

    def test_imminent_contract_logged_at_warning(self):
        # Ends in 5 days — inside the <=7-day WARNING band.
        make_contract(
            name="Imminent Renewal",
            end_date=date.today() + timedelta(days=5),
        )
        job = self._instantiate_job()

        job.run(window_days=60, include_expired=False)

        # At least one WARNING-level call (the per-contract line).
        self.assertGreaterEqual(job.logger.warning.call_count, 1)

    def test_auto_renew_in_notice_window_escalates_to_warning(self):
        # Contract ends in 30 days, but notice period is 60 days — so we are
        # already PAST the notice deadline. With auto_renew=True the rubric
        # must escalate even though days_remaining (30) > 7.
        make_contract(
            name="Auto-Renew Locked-In",
            end_date=date.today() + timedelta(days=30),
            notice_period_days=60,
            auto_renew=True,
        )
        job = self._instantiate_job()

        job.run(window_days=90, include_expired=False)

        self.assertGreaterEqual(job.logger.warning.call_count, 1)

    def test_auto_renew_outside_notice_window_stays_info(self):
        # Same notice period (60d) but plenty of room — 200 days remaining
        # means we're 140 days BEFORE the notice deadline.
        make_contract(
            name="Auto-Renew Plenty-of-Time",
            end_date=date.today() + timedelta(days=200),
            notice_period_days=60,
            auto_renew=True,
        )
        job = self._instantiate_job()

        job.run(window_days=365, include_expired=False)

        # No WARNING — rubric stayed at INFO.
        self.assertEqual(job.logger.warning.call_count, 0)

    def test_no_contracts_in_window_logs_summary_only(self):
        job = self._instantiate_job()

        count = job.run(window_days=30, include_expired=False)

        self.assertEqual(count, 0)
        # Single INFO summary, no WARNING.
        self.assertEqual(job.logger.warning.call_count, 0)
        self.assertGreaterEqual(job.logger.info.call_count, 1)

    def test_include_expired_picks_up_past_contracts(self):
        make_contract(
            name="Already Lapsed",
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=10),
        )
        job = self._instantiate_job()

        # include_expired=False — should skip it.
        count_excluded = job.run(window_days=60, include_expired=False)
        self.assertEqual(count_excluded, 0)

        job2 = self._instantiate_job()
        count_included = job2.run(window_days=60, include_expired=True)
        self.assertEqual(count_included, 1)


class CoverageGapJobTests(TestCase):
    """Verify CoverageGapJob walks Devices and reports the uncovered ones."""

    def _instantiate_job(self):
        job = CoverageGapJob()
        job.logger = MagicMock()
        return job

    def test_uncovered_device_is_reported(self):
        make_device(name="uncovered-01")
        job = self._instantiate_job()

        uncovered_count = job.run(location=None)

        self.assertEqual(uncovered_count, 1)
        self.assertGreaterEqual(job.logger.warning.call_count, 1)

    def test_covered_device_is_skipped(self):
        device = make_device(name="covered-01")
        contract = make_contract(name="Has Coverage")
        assign(contract, device)
        job = self._instantiate_job()

        uncovered_count = job.run(location=None)

        self.assertEqual(uncovered_count, 0)

    def test_tenant_covered_device_is_skipped(self):
        # Coverage at tenant level — the helper's transitive walk should
        # mark this device as covered without a direct assignment.
        tenant = make_tenant("CoveringTenant")
        make_device(name="tenant-covered-01", tenant=tenant)
        contract = make_contract(name="Tenant Coverage")
        assign(contract, tenant)
        job = self._instantiate_job()

        uncovered_count = job.run(location=None)

        self.assertEqual(uncovered_count, 0)

    def test_location_filter_narrows_walk(self):
        target_loc = make_location(name="InScope")
        other_loc = make_location(name="OutOfScope")
        make_device(name="in-scope", location=target_loc)
        make_device(name="out-of-scope", location=other_loc)
        job = self._instantiate_job()

        uncovered_count = job.run(location=target_loc)

        # Only the in-scope device contributes to the count.
        self.assertEqual(uncovered_count, 1)

    def test_mixed_population_counts_only_uncovered(self):
        covered_device = make_device(name="mixed-covered")
        make_device(name="mixed-uncovered")
        contract = make_contract(name="Selective Coverage")
        assign(contract, covered_device)
        job = self._instantiate_job()

        uncovered_count = job.run(location=None)

        self.assertEqual(uncovered_count, 1)
