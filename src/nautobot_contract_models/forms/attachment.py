"""Forms for :class:`InvoiceAttachment` and :class:`ContractAttachment`."""

from django import forms
from nautobot.apps.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotFilterForm,
    NautobotModelForm,
)

from nautobot_contract_models.models import (
    Contract,
    ContractAttachment,
    Invoice,
    InvoiceAttachment,
)


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


class ContractAttachmentForm(NautobotModelForm):
    """Create / edit form. The ``file`` field renders as a native file picker."""

    contract = DynamicModelChoiceField(queryset=Contract.objects.all())

    class Meta:
        """Meta."""

        model = ContractAttachment
        fields = ["contract", "file", "description", "tags"]


class ContractAttachmentFilterForm(NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = ContractAttachment
    q = forms.CharField(required=False, label="Search")
    contract = DynamicModelMultipleChoiceField(queryset=Contract.objects.all(), required=False)
