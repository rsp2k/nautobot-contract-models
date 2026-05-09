"""FilterSet for :class:`CostSnapshot`.

Used by the API viewset to support date-range and currency filters
without exposing the full BaseFilterSet field surface (which would
include defaults like `created`, `last_updated` that don't apply to
write-once telemetry).
"""

import django_filters
from nautobot.apps.filters import BaseFilterSet

from nautobot_contract_models.models import CostSnapshot


class CostSnapshotFilterSet(BaseFilterSet):
    """API filter for :class:`CostSnapshot` — date range + currency."""

    snapshot_date__gte = django_filters.DateFilter(
        field_name="snapshot_date",
        lookup_expr="gte",
        label="Snapshot date on or after (YYYY-MM-DD)",
    )
    snapshot_date__lte = django_filters.DateFilter(
        field_name="snapshot_date",
        lookup_expr="lte",
        label="Snapshot date on or before (YYYY-MM-DD)",
    )

    class Meta:
        """Meta."""

        model = CostSnapshot
        fields = ["id", "snapshot_date", "currency"]
