"""FilterSets for :class:`InvoiceAttachment` and :class:`ContractAttachment`."""

from nautobot.apps.filters import NaturalKeyOrPKMultipleChoiceFilter, NautobotFilterSet, SearchFilter

from nautobot_contract_models.models import (
    Contract,
    ContractAttachment,
    Invoice,
    InvoiceAttachment,
)


class InvoiceAttachmentFilterSet(NautobotFilterSet):
    """List-view filter set for :class:`InvoiceAttachment`."""

    q = SearchFilter(
        filter_predicates={
            "description": "icontains",
            "file": "icontains",
        },
    )
    invoice = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Invoice.objects.all(),
        to_field_name="invoice_number",
        label="Invoice (number or ID)",
    )

    class Meta:
        """Meta."""

        model = InvoiceAttachment
        fields = ["id", "invoice", "description"]


class ContractAttachmentFilterSet(NautobotFilterSet):
    """List-view filter set for :class:`ContractAttachment`."""

    q = SearchFilter(
        filter_predicates={
            "description": "icontains",
            "file": "icontains",
        },
    )
    contract = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Contract.objects.all(),
        to_field_name="name",
        label="Contract (name or ID)",
    )

    class Meta:
        """Meta."""

        model = ContractAttachment
        fields = ["id", "contract", "description"]
