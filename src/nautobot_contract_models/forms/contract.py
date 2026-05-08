"""Forms for :class:`Contract`."""

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
from nautobot.tenancy.models import Tenant

from nautobot_contract_models.models import Contract, ServiceProvider


class ContractForm(NautobotModelForm):
    """Create / edit form."""

    provider = DynamicModelChoiceField(queryset=ServiceProvider.objects.all())
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)

    class Meta:
        """Meta."""

        model = Contract
        fields = [
            "name",
            "contract_number",
            "provider",
            "tenant",
            "status",
            "start_date",
            "end_date",
            "renewal_terms",
            "recurring_cost",
            "one_time_cost",
            "currency",
            "description",
            "comments",
            "tags",
        ]
        widgets = {
            "start_date": DatePicker(),
            "end_date": DatePicker(),
        }


class ContractFilterForm(StatusModelFilterFormMixin, NautobotFilterForm):
    """Filter form (sidebar on the list view)."""

    model = Contract
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    contract_number = forms.CharField(required=False)
    provider = DynamicModelMultipleChoiceField(queryset=ServiceProvider.objects.all(), required=False)
    tenant = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False)
    currency = forms.CharField(required=False)


class ContractBulkEditForm(StatusModelBulkEditFormMixin, TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Bulk-edit form (multi-select on the list view)."""

    pk = forms.ModelMultipleChoiceField(queryset=Contract.objects.all(), widget=forms.MultipleHiddenInput)
    provider = DynamicModelChoiceField(queryset=ServiceProvider.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    renewal_terms = forms.CharField(max_length=255, required=False)
    currency = forms.CharField(max_length=3, required=False)

    class Meta:
        """Meta."""

        nullable_fields = ["tenant", "renewal_terms"]
