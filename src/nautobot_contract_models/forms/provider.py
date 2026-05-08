"""Forms for :class:`ServiceProvider`."""

from django import forms
from nautobot.apps.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    TagsBulkEditFormMixin,
)

from nautobot_contract_models.models import ServiceProvider


class ServiceProviderForm(NautobotModelForm):
    """Create / edit form."""

    class Meta:
        """Meta."""

        model = ServiceProvider
        fields = [
            "name",
            "account_number",
            "portal_url",
            "support_phone",
            "description",
            "comments",
            "tags",
        ]


class ServiceProviderFilterForm(NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = ServiceProvider
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    account_number = forms.CharField(required=False)


class ServiceProviderBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Bulk-edit form (multi-select on the list view)."""

    pk = forms.ModelMultipleChoiceField(queryset=ServiceProvider.objects.all(), widget=forms.MultipleHiddenInput)
    portal_url = forms.URLField(required=False)
    support_phone = forms.CharField(max_length=50, required=False)
    description = forms.CharField(max_length=200, required=False)

    class Meta:
        """Meta."""

        nullable_fields = ["portal_url", "support_phone", "description"]
