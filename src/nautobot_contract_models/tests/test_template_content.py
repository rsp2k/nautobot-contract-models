"""Tests for the Device-detail Active Contracts TemplateExtension — Phase 20.

We exercise the panel's data shape directly (instantiate the
``DeviceActiveContracts`` extension and inspect ``self.rows``) rather than
asserting on rendered HTML. The HTML rendering goes through Nautobot's
Device detail view, which is tested by Nautobot core; what we care about
is that:

1. A device with a direct ContractAssignment shows it with source="direct".
2. A device with no direct assignment but with a tenant-level assignment
   shows it with source="via Tenant: ACME Corp".
3. Same for location.
4. A device with no coverage shows zero rows.
5. The panel doesn't break when the device has no tenant/location at all.
"""

from nautobot.core.testing import TestCase

from nautobot_contract_models.template_content import DeviceActiveContracts, _source_label

from .fixtures import assign, make_contract, make_device, make_location, make_tenant


def _make_extension_for(device):
    """Construct the TemplateExtension with the minimal context shape it expects."""
    return DeviceActiveContracts({"object": device})


class DeviceActiveContractsRowsTests(TestCase):
    """The panel's `rows` list reflects direct + transitive coverage."""

    def test_no_coverage_renders_empty(self):
        device = make_device(name="dev-uncovered")
        ext = _make_extension_for(device)
        self.assertEqual(ext.rows, [])

    def test_direct_assignment_renders_with_source_direct(self):
        device = make_device(name="dev-direct")
        contract = make_contract(name="Direct Coverage")
        assign(contract, device)
        ext = _make_extension_for(device)
        self.assertEqual(len(ext.rows), 1)
        self.assertEqual(ext.rows[0]["contract"], contract)
        self.assertEqual(ext.rows[0]["source_label"], "direct")

    def test_tenant_level_assignment_renders_with_via_tenant(self):
        tenant = make_tenant(name="Tenant-ACME")
        location = make_location(name="HQ-tenant-test", tenant=tenant)
        device = make_device(name="dev-tenant", location=location, tenant=tenant)
        contract = make_contract(name="Tenant-Wide Contract")
        assign(contract, tenant)
        ext = _make_extension_for(device)
        self.assertEqual(len(ext.rows), 1)
        self.assertEqual(ext.rows[0]["source_label"], "via Tenant: Tenant-ACME")

    def test_location_level_assignment_renders_with_via_location(self):
        location = make_location(name="LOC-DCFLOOR1")
        device = make_device(name="dev-loc", location=location)
        contract = make_contract(name="Location-Wide Contract")
        assign(contract, location)
        ext = _make_extension_for(device)
        self.assertEqual(len(ext.rows), 1)
        self.assertEqual(ext.rows[0]["source_label"], "via Location: LOC-DCFLOOR1")

    def test_direct_and_inherited_both_appear(self):
        tenant = make_tenant(name="Tenant-DualCoverage")
        location = make_location(name="LOC-DualCoverage", tenant=tenant)
        device = make_device(name="dev-dual", location=location, tenant=tenant)
        direct_contract = make_contract(name="Direct")
        tenant_contract = make_contract(name="Tenant-Wide")
        assign(direct_contract, device)
        assign(tenant_contract, tenant)
        ext = _make_extension_for(device)
        self.assertEqual(len(ext.rows), 2)
        labels = {row["source_label"] for row in ext.rows}
        self.assertIn("direct", labels)
        self.assertIn("via Tenant: Tenant-DualCoverage", labels)


class SourceLabelHelperTests(TestCase):
    """Pure-function tests on _source_label() — the heart of the panel's data."""

    def test_direct_device_assignment(self):
        device = make_device(name="src-direct")
        contract = make_contract(name="Direct")
        assignment = assign(contract, device)
        self.assertEqual(_source_label(assignment, device), "direct")

    def test_tenant_assignment(self):
        tenant = make_tenant(name="SrcLabelTenant")
        location = make_location(name="loc-src", tenant=tenant)
        device = make_device(name="src-via-tenant", location=location, tenant=tenant)
        contract = make_contract(name="C-tenant")
        assignment = assign(contract, tenant)
        self.assertEqual(_source_label(assignment, device), "via Tenant: SrcLabelTenant")
