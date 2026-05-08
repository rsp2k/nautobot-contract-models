"""Forms for :class:`Invoice`."""

from django import forms
from nautobot.apps.forms import (
    DatePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)

from nautobot_contract_models.models import Contract, Invoice


class InvoiceForm(NautobotModelForm):
    """Create / edit form."""

    contract = DynamicModelChoiceField(queryset=Contract.objects.all())

    class Meta:
        """Meta."""

        model = Invoice
        fields = [
            "contract",
            "invoice_number",
            "period_start",
            "period_end",
            "invoice_date",
            "paid_date",
            "total_amount",
            "currency",
            "status",
            "description",
            "comments",
            "tags",
        ]
        widgets = {
            "period_start": DatePicker(),
            "period_end": DatePicker(),
            "invoice_date": DatePicker(),
            "paid_date": DatePicker(),
        }


class InvoiceFilterForm(StatusModelFilterFormMixin, NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = Invoice
    q = forms.CharField(required=False, label="Search")
    invoice_number = forms.CharField(required=False)
    contract = DynamicModelMultipleChoiceField(queryset=Contract.objects.all(), required=False)
    currency = forms.CharField(required=False)


class InvoiceBulkEditForm(StatusModelBulkEditFormMixin, TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Bulk-edit form (multi-select on the list view)."""

    pk = forms.ModelMultipleChoiceField(queryset=Invoice.objects.all(), widget=forms.MultipleHiddenInput)
    paid_date = forms.DateField(required=False, widget=DatePicker())
    currency = forms.CharField(max_length=3, required=False)

    class Meta:
        """Meta."""

        nullable_fields = ["paid_date"]
