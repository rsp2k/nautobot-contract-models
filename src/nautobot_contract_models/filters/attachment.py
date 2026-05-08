"""FilterSet for :class:`InvoiceAttachment`."""

from nautobot.apps.filters import NaturalKeyOrPKMultipleChoiceFilter, NautobotFilterSet, SearchFilter

from nautobot_contract_models.models import Invoice, InvoiceAttachment


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
