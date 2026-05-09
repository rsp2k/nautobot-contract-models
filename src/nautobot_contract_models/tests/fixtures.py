"""Shared fixture builder for the integration test suite.

Why a builder rather than per-test ``setUp`` boilerplate?
    Nautobot's Device requires a long FK chain (LocationType, Location, Manufacturer,
    DeviceType, Role, Status). Reproducing that in every test method makes the
    actual assertions disappear in scaffolding. The builder pattern below
    constructs the full Tenant → Location → Device hierarchy in a single call
    so the test bodies stay focused on coverage logic.

Each helper returns the created object so individual tests can attach
ContractAssignments at any level of the ancestry.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant

from nautobot_contract_models.models import Contract, ContractAssignment, ServiceProvider


def _ensure_active_status(model):
    """Get-or-extend the 'Active' Status to cover ``model``.

    Nautobot's bootstrap creates an 'Active' status; we just need to make sure
    its ``content_types`` includes the model we're about to create. Doing this
    repeatedly is safe — the M2M `add()` is idempotent.
    """
    status = Status.objects.get(name="Active")
    status.content_types.add(ContentType.objects.get_for_model(model))
    return status


def make_tenant(name="ACME Corp"):
    """Create (or return) a Tenant with the given name."""
    tenant, _ = Tenant.objects.get_or_create(name=name)
    return tenant


def make_location(name="HQ", tenant=None):
    """Create a leaf Location (no parent), with required LocationType + Status."""
    loc_type, _ = LocationType.objects.get_or_create(name="Site", defaults={"nestable": False})
    loc_type.content_types.add(ContentType.objects.get_for_model(Device))
    status = _ensure_active_status(Location)
    location, _ = Location.objects.get_or_create(
        name=name,
        defaults={"location_type": loc_type, "status": status, "tenant": tenant},
    )
    return location


def make_device(name="dev-01", location=None, tenant=None):
    """Create a Device with all the FK-chain it needs.

    If ``location`` or ``tenant`` aren't provided, we create defaults so this
    helper can be called standalone. Tests that want shared parents should
    create them first and pass them in.
    """
    if location is None:
        location = make_location()
    manufacturer, _ = Manufacturer.objects.get_or_create(name="TestCo")
    device_type, _ = DeviceType.objects.get_or_create(manufacturer=manufacturer, model="TestModel-9000")
    role, _ = Role.objects.get_or_create(name="leaf-switch")
    role.content_types.add(ContentType.objects.get_for_model(Device))
    status = _ensure_active_status(Device)
    device = Device.objects.create(
        name=name,
        device_type=device_type,
        role=role,
        location=location,
        status=status,
        tenant=tenant,
    )
    return device


def make_provider(name="VendorCorp"):
    """Create a ServiceProvider."""
    provider, _ = ServiceProvider.objects.get_or_create(name=name)
    return provider


def make_contract(
    name="Master Support Agreement",
    provider=None,
    start_date=None,
    end_date=None,
    **kwargs,
):
    """Create a Contract.

    Defaults: starts a year ago, runs another year (so it's currently active).
    Pass ``start_date`` / ``end_date`` to override for expiration tests.
    """
    if provider is None:
        provider = make_provider()
    if start_date is None:
        start_date = date.today() - timedelta(days=365)
    if end_date is None:
        end_date = date.today() + timedelta(days=365)
    status = _ensure_active_status(Contract)
    return Contract.objects.create(
        name=name,
        provider=provider,
        status=status,
        start_date=start_date,
        end_date=end_date,
        recurring_cost=kwargs.pop("recurring_cost", Decimal("100.00")),
        **kwargs,
    )


def assign(contract, target, **kwargs):
    """Attach ``contract`` to ``target`` via a ContractAssignment.

    ``kwargs`` flow into the assignment (coverage_start, coverage_end,
    is_primary, scope_notes) so tests can exercise per-assignment scope.
    """
    return ContractAssignment.objects.create(
        contract=contract,
        content_type=ContentType.objects.get_for_model(type(target)),
        object_id=target.pk,
        **kwargs,
    )
