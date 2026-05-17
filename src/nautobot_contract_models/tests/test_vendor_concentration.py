"""Tests for cost.vendor_concentration() and the home-dashboard rollup — Phase 20.

We exercise both layers:
- `cost.vendor_concentration` (pure helper): correct per-currency math.
- `homepage.get_vendor_concentration` (request-driven): threshold flag,
  display-ready percent strings.
"""

from decimal import Decimal

from nautobot.core.testing import TestCase

from nautobot_contract_models import cost, homepage

from .fixtures import make_contract, make_provider


class VendorConcentrationHelperTests(TestCase):
    """Pure-function tests on cost.vendor_concentration()."""

    def test_empty_fleet_returns_empty(self):
        self.assertEqual(cost.vendor_concentration(), {})

    def test_single_vendor_single_currency_is_100pct(self):
        cisco = make_provider(name="VC-Cisco")
        make_contract(name="VC-only", provider=cisco, recurring_cost=Decimal("1000.00"))
        result = cost.vendor_concentration()
        self.assertIn("USD", result)
        self.assertEqual(result["USD"]["top_vendor"], cisco)
        self.assertEqual(result["USD"]["top_vendor_pct"], Decimal("1"))

    def test_two_vendors_share_burn_correctly(self):
        cisco = make_provider(name="VC-Cisco-2")
        juniper = make_provider(name="VC-Juniper-2")
        # Cisco $400, Juniper $600 → Juniper is 60% of $1000 burn
        make_contract(name="VC-cisco-1", provider=cisco, recurring_cost=Decimal("400.00"))
        make_contract(name="VC-juniper-1", provider=juniper, recurring_cost=Decimal("600.00"))
        result = cost.vendor_concentration()
        self.assertIn("USD", result)
        self.assertEqual(result["USD"]["top_vendor"], juniper)
        # 600/1000 = 0.6
        self.assertEqual(result["USD"]["top_vendor_pct"], Decimal("0.6"))
        self.assertEqual(result["USD"]["total_burn"], Decimal("1000.00"))

    def test_currencies_treated_independently(self):
        usd_v = make_provider(name="VC-USD-vendor")
        eur_v = make_provider(name="VC-EUR-vendor")
        # USD vendor at 100% of USD, EUR vendor at 100% of EUR — should NOT
        # merge into a single 50/50 split. Per-currency only.
        make_contract(name="VC-usd", provider=usd_v, recurring_cost=Decimal("500.00"), currency="USD")
        make_contract(name="VC-eur", provider=eur_v, recurring_cost=Decimal("500.00"), currency="EUR")
        result = cost.vendor_concentration()
        self.assertEqual(set(result.keys()), {"USD", "EUR"})
        self.assertEqual(result["USD"]["top_vendor"], usd_v)
        self.assertEqual(result["EUR"]["top_vendor"], eur_v)
        self.assertEqual(result["USD"]["top_vendor_pct"], Decimal("1"))


class HomepageRollupTests(TestCase):
    """homepage.get_vendor_concentration: threshold + display formatting."""

    def test_below_default_threshold_does_not_flag(self):
        # Default threshold is 50%. A 40/60 split flags the top vendor (60% >= 50%).
        # Use a 70/30 split to be clearly below threshold for one currency.
        a = make_provider(name="HR-A")
        b = make_provider(name="HR-B")
        make_contract(name="HR-a1", provider=a, recurring_cost=Decimal("300.00"))
        make_contract(name="HR-b1", provider=b, recurring_cost=Decimal("700.00"))
        # That puts HR-B at 70%, which IS above 50% — flag should fire.
        result = homepage.get_vendor_concentration(request=None)
        flagged = [r for r in result["rows"] if r["flagged"]]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["top_vendor"], b)

    def test_balanced_three_way_does_not_flag(self):
        # ~33% each → no row exceeds the default 50% threshold.
        for name in ("HRBalA", "HRBalB", "HRBalC"):
            provider = make_provider(name=name)
            make_contract(name=f"HR-{name}", provider=provider, recurring_cost=Decimal("100.00"))
        result = homepage.get_vendor_concentration(request=None)
        flagged = [r for r in result["rows"] if r["flagged"]]
        self.assertEqual(flagged, [])

    def test_pct_label_is_pre_formatted_string(self):
        a = make_provider(name="HR-Label")
        make_contract(name="HR-pct-label", provider=a, recurring_cost=Decimal("100.00"))
        result = homepage.get_vendor_concentration(request=None)
        self.assertEqual(result["rows"][0]["top_vendor_pct_label"], "100%")
        self.assertEqual(result["threshold_pct_label"], "50%")
