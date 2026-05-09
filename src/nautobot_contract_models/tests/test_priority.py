"""Tests for the centralized action-priority rubric.

What we're verifying:

1. URGENT — auto_renew + in notice window
2. WARNING — within 7 days regardless of notice
3. WARNING — in notice window without auto-renew
4. INFO — within window but outside urgency bands
5. None — no end_date (defensive — the queryset normally excludes these)
6. The same rubric drives ``contracts_needing_action`` ordering
"""

from datetime import date, timedelta
from decimal import Decimal

from nautobot.core.testing import TestCase

from nautobot_contract_models import priority

from .fixtures import make_contract


class ActionPriorityTests(TestCase):
    def test_auto_renew_in_notice_window_is_urgent(self):
        # End in 30 days, notice 60 → notice deadline was 30 days ago.
        contract = make_contract(
            name="lock-in-risk",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=30),
            notice_period_days=60,
            auto_renew=True,
        )
        self.assertEqual(priority.action_priority(contract), priority.URGENT)

    def test_imminent_contract_is_warning(self):
        # 5 days remaining, no notice/auto-renew → triggered by <=7 day band.
        contract = make_contract(
            name="imminent",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=5),
        )
        self.assertEqual(priority.action_priority(contract), priority.WARNING)

    def test_in_notice_window_without_auto_renew_is_warning(self):
        # End in 30 days, notice 60, auto_renew=False → in notice but not urgent.
        contract = make_contract(
            name="termination-deadline",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=30),
            notice_period_days=60,
            auto_renew=False,
        )
        self.assertEqual(priority.action_priority(contract), priority.WARNING)

    def test_far_future_contract_is_info(self):
        # 90 days out, no notice, no auto-renew → just heads-up.
        contract = make_contract(
            name="distant",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=90),
        )
        self.assertEqual(priority.action_priority(contract), priority.INFO)

    def test_auto_renew_outside_notice_window_is_info(self):
        # 200 days out, notice 60. Notice deadline is 140 days out, NOT today.
        contract = make_contract(
            name="auto-but-far",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=200),
            notice_period_days=60,
            auto_renew=True,
        )
        self.assertEqual(priority.action_priority(contract), priority.INFO)

    def test_zero_notice_period_disables_notice_window(self):
        # notice_period_days=0 means there's no notice obligation.
        contract = make_contract(
            name="no-notice-clause",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=30),
            notice_period_days=0,
            auto_renew=True,
        )
        # 30 days remaining > 7 (not imminent), notice disabled (not urgent).
        self.assertEqual(priority.action_priority(contract), priority.INFO)


class ContractsNeedingActionTests(TestCase):
    def test_urgent_contracts_sort_first(self):
        # Two contracts in the window: one urgent, one info-only.
        make_contract(
            name="info-row",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=50),
        )
        make_contract(
            name="urgent-row",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=30),
            notice_period_days=60,
            auto_renew=True,
        )
        rows = priority.contracts_needing_action(window_days=90)
        names = [contract.name for contract, _ in rows]
        self.assertEqual(names[0], "urgent-row")
        # Tier of first row matches.
        self.assertEqual(rows[0][1], priority.URGENT)

    def test_expired_contracts_excluded(self):
        # Already-lapsed: end_date yesterday.
        make_contract(
            name="lapsed",
            recurring_cost=Decimal("100"),
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=1),
        )
        rows = priority.contracts_needing_action(window_days=60)
        self.assertEqual(rows, [])

    def test_window_boundary_inclusive(self):
        # End date exactly window_days out should be included.
        make_contract(
            name="boundary",
            recurring_cost=Decimal("100"),
            end_date=date.today() + timedelta(days=60),
        )
        rows = priority.contracts_needing_action(window_days=60)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0].name, "boundary")
