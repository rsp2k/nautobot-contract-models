"""UI viewset for :class:`Contract`."""

from nautobot.apps.views import NautobotUIViewSet

from nautobot_contract_models.api.serializers import ContractSerializer
from nautobot_contract_models.filters import ContractFilterSet
from nautobot_contract_models.forms import ContractBulkEditForm, ContractFilterForm, ContractForm
from nautobot_contract_models.models import Contract
from nautobot_contract_models.tables import ContractTable


class ContractUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`Contract`."""

    bulk_update_form_class = ContractBulkEditForm
    filterset_class = ContractFilterSet
    filterset_form_class = ContractFilterForm
    form_class = ContractForm
    queryset = Contract.objects.select_related("provider", "tenant", "status")
    serializer_class = ContractSerializer
    table_class = ContractTable
