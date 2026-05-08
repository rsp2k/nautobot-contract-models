"""FilterSet for :class:`ContractAssignment`."""

from nautobot.apps.filters import NaturalKeyOrPKMultipleChoiceFilter, NautobotFilterSet

from nautobot_contract_models.models import Contract, ContractAssignment


class ContractAssignmentFilterSet(NautobotFilterSet):
    """List-view filter set for :class:`ContractAssignment`.

    No SearchFilter — there's no useful free-text field on this model. Filter
    by contract or content_type instead.
    """

    contract = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Contract.objects.all(),
        to_field_name="name",
        label="Contract (name or ID)",
    )

    class Meta:
        """Meta."""

        model = ContractAssignment
        fields = ["id", "contract", "content_type", "object_id"]
