"""Forms for :class:`InvoiceAttachment`."""

from django import forms
from nautobot.apps.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotFilterForm,
    NautobotModelForm,
)

from nautobot_contract_models.models import Invoice, InvoiceAttachment


class InvoiceAttachmentForm(NautobotModelForm):
    """Create / edit form. The ``file`` field renders as a native file picker."""

    invoice = DynamicModelChoiceField(queryset=Invoice.objects.all())

    class Meta:
        """Meta."""

        model = InvoiceAttachment
        fields = ["invoice", "file", "description", "tags"]


class InvoiceAttachmentFilterForm(NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = InvoiceAttachment
    q = forms.CharField(required=False, label="Search")
    invoice = DynamicModelMultipleChoiceField(queryset=Invoice.objects.all(), required=False)
