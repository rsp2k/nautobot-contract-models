"""UI viewset for :class:`Contract`."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel

from nautobot_contract_models.api.serializers import ContractSerializer
from nautobot_contract_models.filters import ContractFilterSet
from nautobot_contract_models.forms import ContractBulkEditForm, ContractFilterForm, ContractForm
from nautobot_contract_models.models import Contract
from nautobot_contract_models.tables import ContractAssignmentTable, ContractTable, InvoiceTable


class ContractUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`Contract`."""

    bulk_update_form_class = ContractBulkEditForm
    filterset_class = ContractFilterSet
    filterset_form_class = ContractFilterForm
    form_class = ContractForm
    queryset = Contract.objects.select_related("provider", "tenant", "status")
    serializer_class = ContractSerializer
    table_class = ContractTable

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
                label="Invoices",
                table_class=InvoiceTable,
                table_filter="contract",
                exclude_columns=["contract"],
            ),
            ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=300,
                label="Coverage (Contract Assignments)",
                table_class=ContractAssignmentTable,
                table_filter="contract",
                exclude_columns=["contract"],
            ),
        ),
    )
