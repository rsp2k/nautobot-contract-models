"""Tests for cost.detect_anomalies + CostAnomalyJob.

What we're verifying:

1. A 25% jump exceeds default threshold (20%) → anomaly reported
2. A 5% drift is below threshold → no anomaly
3. An identical baseline → no anomaly
4. Zero baseline + nonzero current → reported as NEW (pct_change=None)
5. Each currency considered independently
6. The Job logs WARNINGs for anomalies and INFO for the summary
7. No history → Job logs an INFO line, returns 0
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from nautobot.core.testing import TestCase

from nautobot_contract_models import cost
from nautobot_contract_models.jobs import CostAnomalyJob
from nautobot_contract_models.models import CostSnapshot


def _snap(weeks_ago, currency="USD", **values):
    return CostSnapshot.objects.create(
        snapshot_date=date.today() - timedelta(weeks=weeks_ago),
        currency=currency,
        **values,
    )


class DetectAnomaliesTests(TestCase):
    def test_jump_above_threshold_is_reported(self):
        # 4 weeks ago: USD burn 1000. Today: USD burn 1300 (+30%).
        _snap(4, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1300"))

        anomalies = cost.detect_anomalies(threshold=Decimal("0.20"), lookback_weeks=4)

        burn = next(a for a in anomalies if a["metric"] == "monthly_burn")
        self.assertEqual(burn["direction"], "up")
        self.assertGreater(burn["pct_change"], Decimal("0.20"))
        self.assertEqual(burn["prev_value"], Decimal("1000"))
        self.assertEqual(burn["current_value"], Decimal("1300"))

    def test_small_drift_below_threshold_skipped(self):
        # 5% jump shouldn't trigger at default 20% threshold.
        _snap(4, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1050"))

        anomalies = cost.detect_anomalies(threshold=Decimal("0.20"), lookback_weeks=4)
        burn_anoms = [a for a in anomalies if a["metric"] == "monthly_burn"]
        self.assertEqual(burn_anoms, [])

    def test_identical_baseline_not_reported(self):
        _snap(4, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1000"))

        anomalies = cost.detect_anomalies()
        self.assertEqual(anomalies, [])

    def test_new_currency_reported_as_new(self):
        # No snapshot 4 weeks ago — only today.
        _snap(0, currency="EUR", monthly_burn=Decimal("500"))

        anomalies = cost.detect_anomalies(lookback_weeks=4)
        eur = [a for a in anomalies if a["currency"] == "EUR" and a["metric"] == "monthly_burn"]
        self.assertEqual(len(eur), 1)
        self.assertIsNone(eur[0]["pct_change"])
        self.assertEqual(eur[0]["direction"], "up")

    def test_per_currency_independence(self):
        # USD jumps, EUR is flat — only USD should be reported.
        _snap(4, currency="USD", monthly_burn=Decimal("1000"))
        _snap(0, currency="USD", monthly_burn=Decimal("1500"))
        _snap(4, currency="EUR", monthly_burn=Decimal("500"))
        _snap(0, currency="EUR", monthly_burn=Decimal("500"))

        anomalies = cost.detect_anomalies(threshold=Decimal("0.20"))
        currencies_with_anomalies = {a["currency"] for a in anomalies}
        self.assertIn("USD", currencies_with_anomalies)
        self.assertNotIn("EUR", currencies_with_anomalies)

    def test_lookback_uses_most_recent_at_or_before_target(self):
        # Snapshot 5 weeks ago should be picked when target is 4 weeks
        # AND no exact-week match exists.
        _snap(5, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1300"))

        anomalies = cost.detect_anomalies(threshold=Decimal("0.20"), lookback_weeks=4)
        burn = next((a for a in anomalies if a["metric"] == "monthly_burn"), None)
        self.assertIsNotNone(burn)
        self.assertEqual(burn["prev_value"], Decimal("1000"))


class CostAnomalyJobTests(TestCase):
    def _instantiate_job(self):
        job = CostAnomalyJob()
        job.logger = MagicMock()
        return job

    def test_anomaly_logged_at_warning(self):
        _snap(4, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1500"))
        job = self._instantiate_job()

        result = job.run(threshold_pct=20, lookback_weeks=4)

        self.assertGreaterEqual(result, 1)
        self.assertGreaterEqual(job.logger.warning.call_count, 1)

    def test_no_anomalies_logs_info_only(self):
        _snap(4, monthly_burn=Decimal("1000"))
        _snap(0, monthly_burn=Decimal("1010"))  # 1% drift
        job = self._instantiate_job()

        result = job.run(threshold_pct=20, lookback_weeks=4)

        self.assertEqual(result, 0)
        self.assertEqual(job.logger.warning.call_count, 0)
        self.assertGreaterEqual(job.logger.info.call_count, 1)

    def test_no_history_logs_info_zero(self):
        # No snapshots at all.
        job = self._instantiate_job()

        result = job.run(threshold_pct=20, lookback_weeks=4)

        self.assertEqual(result, 0)
        self.assertEqual(job.logger.warning.call_count, 0)
