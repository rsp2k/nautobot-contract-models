"""FilterSet for :class:`Contract`."""

from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
)

from nautobot_contract_models.models import Contract, ServiceProvider


class ContractFilterSet(StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet):
    """List-view filter set for :class:`Contract`."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "contract_number": "icontains",
            "description": "icontains",
            "comments": "icontains",
            "renewal_terms": "icontains",
        },
    )
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ServiceProvider.objects.all(),
        to_field_name="name",
        label="Provider (name or ID)",
    )

    class Meta:
        """Meta."""

        model = Contract
        # Structured choice fields must be listed here for the FilterForm's
        # MultipleChoiceField to actually filter the queryset. Phase 7 added
        # the form widgets but missed updating this list — Phase 8 also adds
        # billing_period and backfills the missing entries.
        fields = [
            "id",
            "name",
            "contract_number",
            "currency",
            "start_date",
            "end_date",
            "contract_type",
            "coverage_hours",
            "response_time",
            "restoration_time",
            "auto_renew",
            "billing_period",
        ]
