"""UI viewset for :class:`Invoice`."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel

from nautobot_contract_models.api.serializers import InvoiceSerializer
from nautobot_contract_models.filters import InvoiceFilterSet
from nautobot_contract_models.forms import InvoiceBulkEditForm, InvoiceFilterForm, InvoiceForm
from nautobot_contract_models.models import Invoice
from nautobot_contract_models.tables import InvoiceTable


class InvoiceUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`Invoice`."""

    bulk_update_form_class = InvoiceBulkEditForm
    filterset_class = InvoiceFilterSet
    filterset_form_class = InvoiceFilterForm
    form_class = InvoiceForm
    queryset = Invoice.objects.select_related("contract", "status")
    serializer_class = InvoiceSerializer
    table_class = InvoiceTable

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )
