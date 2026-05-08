"""Forms for :class:`ContractAssignment`."""

from django import forms
from django.contrib.contenttypes.models import ContentType
from nautobot.apps.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NautobotFilterForm,
    NautobotModelForm,
)

from nautobot_contract_models.models import Contract, ContractAssignment


class ContractAssignmentForm(NautobotModelForm):
    """Create / edit form.

    The :attr:`object_id` field is a UUIDField on the model — at v1 we present
    it as a free-form input. A future enhancement: dynamically swap in a
    DynamicModelChoiceField that filters by the selected ``content_type`` so
    operators don't have to paste UUIDs.
    """

    contract = DynamicModelChoiceField(queryset=Contract.objects.all())

    class Meta:
        """Meta."""

        model = ContractAssignment
        fields = ["contract", "content_type", "object_id"]


class ContractAssignmentFilterForm(NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = ContractAssignment
    q = forms.CharField(required=False, label="Search")
    contract = DynamicModelMultipleChoiceField(queryset=Contract.objects.all(), required=False)
    content_type = forms.ModelMultipleChoiceField(queryset=ContentType.objects.all(), required=False)
