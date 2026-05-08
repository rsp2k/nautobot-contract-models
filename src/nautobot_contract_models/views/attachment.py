"""UI viewset for :class:`InvoiceAttachment`."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel

from nautobot_contract_models.api.serializers import InvoiceAttachmentSerializer
from nautobot_contract_models.filters import InvoiceAttachmentFilterSet
from nautobot_contract_models.forms import InvoiceAttachmentFilterForm, InvoiceAttachmentForm
from nautobot_contract_models.models import InvoiceAttachment
from nautobot_contract_models.tables import InvoiceAttachmentTable


class InvoiceAttachmentUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`InvoiceAttachment`."""

    filterset_class = InvoiceAttachmentFilterSet
    filterset_form_class = InvoiceAttachmentFilterForm
    form_class = InvoiceAttachmentForm
    queryset = InvoiceAttachment.objects.select_related("invoice")
    serializer_class = InvoiceAttachmentSerializer
    table_class = InvoiceAttachmentTable
    # No CSV import — file uploads can't reasonably be imported in bulk.
    action_buttons = ("add",)

    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
        ),
    )
