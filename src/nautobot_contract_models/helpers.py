"""Cross-cutting helpers — query utilities used by Jobs, views, and templates."""

from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot_contract_models.models import ContractAssignment

# Ancestry attributes we walk to find transitive coverage. Each entry is the
# attribute name on the target object that yields an ancestor object. ``None``
# means "the object itself" — included so a direct assignment shows up.
#
# This intentionally matches Nautobot's own DCIM hierarchy. If operators add
# coverage on a Location, every Device at that Location gets that coverage in
# the transitive view; same for Tenant. The list is short on purpose: each
# additional ancestry walk is one more queryset hit.
DEFAULT_ANCESTRY_ATTRS = (None, "tenant", "location", "rack", "device")


def coverage_assignments(target, *, on_date=None, ancestry_attrs=DEFAULT_ANCESTRY_ATTRS):
    """Return ContractAssignments covering ``target``, including via ancestry.

    Looks for assignments whose ``content_type`` + ``object_id`` matches the
    target *or* any reachable ancestor (tenant, location, rack, parent
    device). Filtered to active coverage on ``on_date`` (default today),
    where "active" means:

        - The Contract's start_date <= on_date <= end_date
        - The Assignment's coverage_start (if set) <= on_date
        - The Assignment's coverage_end (if set) >= on_date

    Sorted with primary assignments first, then by contract end_date
    descending (most-recent renewal first).

    The expected pattern: a Device detail page renders this as "Coverage
    (including via Tenant / Location)" so on-call engineers can see the full
    set of contracts that apply, not just the explicit assignments.
    """
    if on_date is None:
        on_date = date.today()

    # Collect (content_type, object_id) pairs for target + each reachable ancestor.
    pairs = []
    for attr in ancestry_attrs:
        if attr is None:
            obj = target
        else:
            obj = getattr(target, attr, None)
            if obj is None:
                continue
        try:
            ct = ContentType.objects.get_for_model(type(obj))
        except (AttributeError, TypeError):
            continue
        pairs.append((ct.id, obj.pk))

    if not pairs:
        return ContractAssignment.objects.none()

    # Build a Q that matches any (content_type_id, object_id) pair.
    pair_filter = Q()
    for ct_id, obj_id in pairs:
        pair_filter |= Q(content_type_id=ct_id, object_id=obj_id)

    qs = (
        ContractAssignment.objects.select_related("contract", "contract__provider", "contract__status")
        .filter(pair_filter)
        .filter(contract__start_date__lte=on_date, contract__end_date__gte=on_date)
        .filter(Q(coverage_start__isnull=True) | Q(coverage_start__lte=on_date))
        .filter(Q(coverage_end__isnull=True) | Q(coverage_end__gte=on_date))
    )

    return qs.order_by("-is_primary", "-contract__end_date", "contract__name")


def has_active_coverage(target, *, on_date=None, ancestry_attrs=DEFAULT_ANCESTRY_ATTRS):
    """Cheap boolean: does ``target`` have any active contract coverage today?

    Used by the CoverageGapJob and the "Uncovered Devices" home dashboard
    panel. Accepts the same ``ancestry_attrs`` knob as
    :func:`coverage_assignments` so callers can narrow the walk (e.g. to
    check direct-only coverage on a Device).
    """
    return coverage_assignments(target, on_date=on_date, ancestry_attrs=ancestry_attrs).exists()
