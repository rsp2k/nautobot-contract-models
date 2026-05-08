"""FilterSet for :class:`Invoice`."""

from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
)

from nautobot_contract_models.models import Contract, Invoice


class InvoiceFilterSet(StatusModelFilterSetMixin, NautobotFilterSet):
    """List-view filter set for :class:`Invoice`."""

    q = SearchFilter(
        filter_predicates={
            "invoice_number": "icontains",
            "description": "icontains",
            "comments": "icontains",
        },
    )
    contract = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Contract.objects.all(),
        to_field_name="name",
        label="Contract (name or ID)",
    )

    class Meta:
        """Meta."""

        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "currency",
            "invoice_date",
            "period_start",
            "period_end",
            "paid_date",
        ]
