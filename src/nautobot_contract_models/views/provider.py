"""UI viewset for :class:`ServiceProvider`."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.models.querysets import count_related
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel

from nautobot_contract_models.api.serializers import ServiceProviderSerializer
from nautobot_contract_models.filters import ServiceProviderFilterSet
from nautobot_contract_models.forms import (
    ServiceProviderBulkEditForm,
    ServiceProviderFilterForm,
    ServiceProviderForm,
)
from nautobot_contract_models.models import Contract, ServiceProvider
from nautobot_contract_models.tables import ContractTable, ServiceProviderTable


class ServiceProviderUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`ServiceProvider`."""

    bulk_update_form_class = ServiceProviderBulkEditForm
    filterset_class = ServiceProviderFilterSet
    filterset_form_class = ServiceProviderFilterForm
    form_class = ServiceProviderForm
    queryset = ServiceProvider.objects.annotate(contract_count=count_related(Contract, "provider"))
    serializer_class = ServiceProviderSerializer
    table_class = ServiceProviderTable

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=200,
                label="Contracts",
                table_class=ContractTable,
                table_filter="provider",
                exclude_columns=["provider"],
            ),
        ),
    )
