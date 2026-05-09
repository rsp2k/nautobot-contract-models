"""Tests for cost.renewal_calendar() — the Phase 9 month-grid helper.

What we're verifying:

1. Default 12-month window returns exactly 12 entries.
2. Custom ``months`` parameter produces that many entries.
3. Empty months render as ``totals={}``, ``contract_count=0``.
4. Contracts ending in a month are counted in that month.
5. Each entry's totals are per-currency (no FX summing).
6. The grid anchors on the first of the current month — partial months
   at the front aren't dropped.
7. Contracts ending after the window aren't counted.
8. Contracts ending before today aren't counted.
"""

from datetime import date
from decimal import Decimal

from nautobot.core.testing import TestCase

from nautobot_contract_models import cost

from .fixtures import make_contract


def _date_in_n_months(n):
    """Return a date n calendar months after today's first-of-month."""
    today = date.today().replace(day=1)
    year, month = today.year, today.month
    total = (month - 1) + n
    new_year = year + total // 12
    new_month = (total % 12) + 1
    # Use day 15 to land safely in the middle of the month regardless of length.
    return date(new_year, new_month, 15)


class RenewalCalendarTests(TestCase):
    def test_default_window_is_twelve_months(self):
        grid = cost.renewal_calendar()
        self.assertEqual(len(grid), 12)

    def test_custom_window_length(self):
        grid = cost.renewal_calendar(months=6)
        self.assertEqual(len(grid), 6)

    def test_empty_months_have_zero_count(self):
        grid = cost.renewal_calendar(months=3)
        for cell in grid:
            self.assertEqual(cell["contract_count"], 0)
            self.assertEqual(cell["totals"], {})

    def test_contract_ending_in_month_is_counted(self):
        # A contract whose end_date is in two months from now.
        target_date = _date_in_n_months(2)
        make_contract(
            name="bucket-test",
            recurring_cost=Decimal("100"),
            billing_period="monthly",
            term_months=12,
            start_date=target_date.replace(year=target_date.year - 1),
            end_date=target_date,
        )

        grid = cost.renewal_calendar(months=6)
        # Find the cell matching target_date's (year, month).
        matching = [cell for cell in grid if cell["year"] == target_date.year and cell["month"] == target_date.month]
        self.assertEqual(len(matching), 1)
        cell = matching[0]
        self.assertEqual(cell["contract_count"], 1)
        # term_months=12 * monthly $100 = $1200 total value
        self.assertEqual(cell["totals"]["USD"], Decimal("1200"))

    def test_per_currency_grouping_in_calendar(self):
        target_date = _date_in_n_months(1)
        make_contract(
            name="usd-cal",
            recurring_cost=Decimal("100"),
            billing_period="monthly",
            term_months=12,
            currency="USD",
            start_date=target_date.replace(year=target_date.year - 1),
            end_date=target_date,
        )
        make_contract(
            name="eur-cal",
            recurring_cost=Decimal("50"),
            billing_period="monthly",
            term_months=12,
            currency="EUR",
            start_date=target_date.replace(year=target_date.year - 1),
            end_date=target_date,
        )

        grid = cost.renewal_calendar(months=3)
        cell = next(c for c in grid if c["year"] == target_date.year and c["month"] == target_date.month)
        self.assertEqual(cell["totals"]["USD"], Decimal("1200"))
        self.assertEqual(cell["totals"]["EUR"], Decimal("600"))
        self.assertEqual(cell["contract_count"], 2)

    def test_grid_anchors_at_first_of_current_month(self):
        # A contract ending today (or earlier this month) MUST appear in
        # the first cell — operators can't lose visibility on partial-month
        # renewals at the window's left edge.
        today = date.today()
        if today.day == 1:
            # Edge case: it's literally the first; pick yesterday's month.
            target = today
        else:
            target = today.replace(day=1)
        make_contract(
            name="this-month",
            recurring_cost=Decimal("100"),
            billing_period="monthly",
            term_months=12,
            start_date=target.replace(year=target.year - 1),
            end_date=target,
        )

        grid = cost.renewal_calendar(months=12)
        first = grid[0]
        self.assertEqual(first["year"], today.year)
        self.assertEqual(first["month"], today.month)
        self.assertEqual(first["contract_count"], 1)

    def test_contract_outside_window_not_counted(self):
        # Contract ending 24 months out won't appear in a 12-month window.
        far_future = _date_in_n_months(24)
        make_contract(
            name="too-far",
            recurring_cost=Decimal("100"),
            billing_period="monthly",
            start_date=far_future.replace(year=far_future.year - 1),
            end_date=far_future,
        )

        grid = cost.renewal_calendar(months=12)
        for cell in grid:
            self.assertEqual(cell["contract_count"], 0)

    def test_already_expired_contract_not_in_calendar(self):
        # End_date in the past month — calendar is forward-looking only.
        from datetime import timedelta

        past = date.today().replace(day=1) - timedelta(days=1)
        make_contract(
            name="expired-pre-window",
            recurring_cost=Decimal("100"),
            billing_period="monthly",
            start_date=past.replace(year=past.year - 1),
            end_date=past,
        )

        grid = cost.renewal_calendar(months=12)
        for cell in grid:
            self.assertEqual(cell["contract_count"], 0)

    def test_label_matches_month_name(self):
        grid = cost.renewal_calendar(months=12)
        labels = {cell["month"]: cell["label"] for cell in grid}
        # At minimum the current month's label is one of the standard 3-letter abbrevs.
        valid_labels = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}
        self.assertIn(labels[date.today().month], valid_labels)
