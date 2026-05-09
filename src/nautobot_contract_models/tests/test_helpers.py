"""Integration tests for the transitive coverage helper.

What we're verifying:

1. Direct assignment — Device with its own ContractAssignment is covered.
2. Tenant ancestry — Device whose Tenant has an assignment is covered.
3. Location ancestry — Device whose Location has an assignment is covered.
4. No coverage — Device with neither direct nor ancestor coverage isn't.
5. Date filtering — expired contracts don't count.
6. Per-assignment scope — coverage_start in the future, coverage_end in the
   past both exclude the assignment.
7. Custom on_date — passing a different reference date selects/excludes
   contracts based on that date instead of today.
8. Custom ancestry_attrs — callers can narrow or broaden the walk.

Each test creates only the minimal hierarchy it needs. The fixtures module
absorbs the FK-chain boilerplate so test bodies stay focused.
"""

from datetime import date, timedelta

from nautobot.core.testing import TestCase

from nautobot_contract_models.helpers import coverage_assignments, has_active_coverage

from .fixtures import assign, make_contract, make_device, make_location, make_tenant


class TransitiveCoverageTests(TestCase):
    """Verify the helper finds coverage via direct + ancestor assignments."""

    def test_device_with_direct_assignment_is_covered(self):
        device = make_device(name="direct-01")
        contract = make_contract(name="Direct Coverage")
        assign(contract, device)

        self.assertTrue(has_active_coverage(device))
        self.assertEqual(coverage_assignments(device).count(), 1)

    def test_device_inherits_tenant_coverage(self):
        tenant = make_tenant("InheritedTenant")
        device = make_device(name="tenant-child", tenant=tenant)
        contract = make_contract(name="Tenant-Level Coverage")
        # Assignment is on the tenant — device has none of its own.
        assign(contract, tenant)

        self.assertTrue(has_active_coverage(device))
        # Walk produced exactly one assignment (the tenant's).
        self.assertEqual(coverage_assignments(device).count(), 1)

    def test_device_inherits_location_coverage(self):
        location = make_location(name="InheritedSite")
        device = make_device(name="loc-child", location=location)
        contract = make_contract(name="Site-Level Coverage")
        assign(contract, location)

        self.assertTrue(has_active_coverage(device))

    def test_device_with_no_coverage_anywhere(self):
        device = make_device(name="lonely-01")

        self.assertFalse(has_active_coverage(device))
        self.assertEqual(coverage_assignments(device).count(), 0)

    def test_expired_contract_does_not_cover(self):
        device = make_device(name="expired-01")
        # Contract that ended yesterday.
        contract = make_contract(
            name="Already Expired",
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=1),
        )
        assign(contract, device)

        self.assertFalse(has_active_coverage(device))

    def test_assignment_with_future_coverage_start(self):
        device = make_device(name="future-coverage-01")
        contract = make_contract(name="Future-Scoped Coverage")
        # Per-assignment coverage_start is 30 days out — even though the
        # contract itself is active.
        assign(contract, device, coverage_start=date.today() + timedelta(days=30))

        self.assertFalse(has_active_coverage(device))

    def test_assignment_with_past_coverage_end(self):
        device = make_device(name="past-coverage-01")
        contract = make_contract(name="Mid-Term-Removal Coverage")
        assign(contract, device, coverage_end=date.today() - timedelta(days=1))

        self.assertFalse(has_active_coverage(device))

    def test_on_date_param_uses_reference_date(self):
        device = make_device(name="historical-01")
        # Contract that ran for all of last year.
        contract = make_contract(
            name="Last Year's Contract",
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=35),
        )
        assign(contract, device)

        # Today: not covered.
        self.assertFalse(has_active_coverage(device))
        # 100 days ago: covered.
        self.assertTrue(has_active_coverage(device, on_date=date.today() - timedelta(days=100)))

    def test_custom_ancestry_attrs_can_skip_levels(self):
        """Passing a narrower ancestry_attrs lets callers ignore inherited coverage."""
        tenant = make_tenant("SkippedAncestry")
        device = make_device(name="narrow-walk-01", tenant=tenant)
        contract = make_contract(name="Tenant-Only Coverage")
        assign(contract, tenant)

        # Default walk includes tenant — covered.
        self.assertTrue(has_active_coverage(device))
        # Walk only the device itself — NOT covered (tenant assignment ignored).
        self.assertFalse(has_active_coverage(device, ancestry_attrs=(None,)))

    def test_primary_assignment_sorts_first(self):
        """is_primary=True assignments appear before others in coverage_assignments."""
        device = make_device(name="multi-cover-01")
        primary = make_contract(name="Primary Vendor", end_date=date.today() + timedelta(days=30))
        secondary = make_contract(name="Backup Vendor", end_date=date.today() + timedelta(days=200))
        assign(secondary, device)
        assign(primary, device, is_primary=True)

        ordered = list(coverage_assignments(device))
        self.assertEqual(ordered[0].contract.name, "Primary Vendor")
