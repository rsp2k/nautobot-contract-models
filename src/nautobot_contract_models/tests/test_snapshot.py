"""Tests for cost.take_snapshot and cost.history.

What we're verifying:

1. take_snapshot creates one row per currency
2. take_snapshot is idempotent on (date, currency) — re-running doesn't duplicate
3. take_snapshot picks up burn / renewal / count from active contracts
4. history returns rows ordered oldest-first within the window
5. history filters by currency when asked
6. coverage_gap_count is captured on the alphabetically-first currency only
"""

from datetime import date, timedelta
from decimal import Decimal

from nautobot.core.testing import TestCase

from nautobot_contract_models import cost
from nautobot_contract_models.models import CostSnapshot

from .fixtures import make_contract


class TakeSnapshotTests(TestCase):
    def test_creates_one_row_per_currency(self):
        make_contract(name="usd-1", recurring_cost=Decimal("100"), currency="USD")
        make_contract(name="eur-1", recurring_cost=Decimal("200"), currency="EUR")

        snapshots = cost.take_snapshot()

        currencies = sorted(s.currency for s in snapshots)
        self.assertEqual(currencies, ["EUR", "USD"])
        self.assertEqual(CostSnapshot.objects.count(), 2)

    def test_idempotent_per_date_currency(self):
        make_contract(name="repeat", recurring_cost=Decimal("100"))

        cost.take_snapshot()
        cost.take_snapshot()

        # Second call updates the same row, doesn't create a new one.
        self.assertEqual(CostSnapshot.objects.count(), 1)

    def test_captures_monthly_burn(self):
        make_contract(name="annual-c", recurring_cost=Decimal("1200"), billing_period="annual")
        # $1200/yr ÷ 12 = $100/mo
        cost.take_snapshot()
        snap = CostSnapshot.objects.get(currency="USD")
        self.assertEqual(snap.monthly_burn, Decimal("100"))

    def test_captures_active_contract_count(self):
        make_contract(name="a", recurring_cost=Decimal("100"))
        make_contract(name="b", recurring_cost=Decimal("100"))
        # An expired contract doesn't count.
        make_contract(
            name="lapsed",
            recurring_cost=Decimal("100"),
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=10),
        )

        cost.take_snapshot()
        snap = CostSnapshot.objects.get(currency="USD")
        self.assertEqual(snap.active_contract_count, 2)

    def test_coverage_gap_count_only_on_first_currency(self):
        # EUR sorts before USD, so EUR gets the gap count; USD's column is null.
        # The single column carries one count per (date) regardless of currencies.
        make_contract(name="usd-1", recurring_cost=Decimal("100"), currency="USD")
        make_contract(name="eur-1", recurring_cost=Decimal("100"), currency="EUR")

        cost.take_snapshot()
        eur = CostSnapshot.objects.get(currency="EUR")
        usd = CostSnapshot.objects.get(currency="USD")
        self.assertIsNotNone(eur.coverage_gap_count)
        self.assertIsNone(usd.coverage_gap_count)


class HistoryTests(TestCase):
    def test_returns_rows_within_window_oldest_first(self):
        # Manually create three weeks of snapshots.
        for weeks_ago in (3, 2, 1):
            CostSnapshot.objects.create(
                snapshot_date=date.today() - timedelta(weeks=weeks_ago),
                currency="USD",
                monthly_burn=Decimal("100") * weeks_ago,
            )

        rows = cost.history(weeks=4)

        # Oldest-first ordering.
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].monthly_burn, Decimal("300"))  # 3 weeks ago
        self.assertEqual(rows[-1].monthly_burn, Decimal("100"))  # 1 week ago

    def test_currency_filter(self):
        CostSnapshot.objects.create(
            snapshot_date=date.today() - timedelta(weeks=1),
            currency="USD",
            monthly_burn=Decimal("100"),
        )
        CostSnapshot.objects.create(
            snapshot_date=date.today() - timedelta(weeks=1),
            currency="EUR",
            monthly_burn=Decimal("200"),
        )

        usd_rows = cost.history(weeks=4, currency="USD")
        self.assertEqual(len(usd_rows), 1)
        self.assertEqual(usd_rows[0].currency, "USD")

    def test_excludes_outside_window(self):
        CostSnapshot.objects.create(
            snapshot_date=date.today() - timedelta(weeks=20),
            currency="USD",
            monthly_burn=Decimal("100"),
        )
        rows = cost.history(weeks=4)
        self.assertEqual(rows, [])
