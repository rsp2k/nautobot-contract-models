"""UI viewset for :class:`ServiceProvider`."""

from nautobot.apps.views import NautobotUIViewSet

from nautobot_contract_models.api.serializers import ServiceProviderSerializer
from nautobot_contract_models.filters import ServiceProviderFilterSet
from nautobot_contract_models.forms import (
    ServiceProviderBulkEditForm,
    ServiceProviderFilterForm,
    ServiceProviderForm,
)
from nautobot_contract_models.models import ServiceProvider
from nautobot_contract_models.tables import ServiceProviderTable


class ServiceProviderUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`ServiceProvider`."""

    bulk_update_form_class = ServiceProviderBulkEditForm
    filterset_class = ServiceProviderFilterSet
    filterset_form_class = ServiceProviderFilterForm
    form_class = ServiceProviderForm
    queryset = ServiceProvider.objects.all()
    serializer_class = ServiceProviderSerializer
    table_class = ServiceProviderTable
