"""UI viewsets for :class:`InvoiceAttachment` and :class:`ContractAttachment`."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel

from nautobot_contract_models.api.serializers import (
    ContractAttachmentSerializer,
    InvoiceAttachmentSerializer,
)
from nautobot_contract_models.filters import (
    ContractAttachmentFilterSet,
    InvoiceAttachmentFilterSet,
)
from nautobot_contract_models.forms import (
    ContractAttachmentFilterForm,
    ContractAttachmentForm,
    InvoiceAttachmentFilterForm,
    InvoiceAttachmentForm,
)
from nautobot_contract_models.models import ContractAttachment, InvoiceAttachment
from nautobot_contract_models.tables import ContractAttachmentTable, InvoiceAttachmentTable

# Action buttons shared by both attachment viewsets — no CSV import (uploads
# don't make sense in bulk-paste form).
_ATTACHMENT_ACTIONS = ("add",)
_ATTACHMENT_DETAIL_PANELS = (
    ObjectFieldsPanel(
        section=SectionChoices.LEFT_HALF,
        weight=100,
        fields="__all__",
    ),
)


class InvoiceAttachmentUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`InvoiceAttachment`."""

    filterset_class = InvoiceAttachmentFilterSet
    filterset_form_class = InvoiceAttachmentFilterForm
    form_class = InvoiceAttachmentForm
    queryset = InvoiceAttachment.objects.select_related("invoice")
    serializer_class = InvoiceAttachmentSerializer
    table_class = InvoiceAttachmentTable
    action_buttons = _ATTACHMENT_ACTIONS
    object_detail_content = ObjectDetailContent(panels=_ATTACHMENT_DETAIL_PANELS)


class ContractAttachmentUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`ContractAttachment`."""

    filterset_class = ContractAttachmentFilterSet
    filterset_form_class = ContractAttachmentFilterForm
    form_class = ContractAttachmentForm
    queryset = ContractAttachment.objects.select_related("contract")
    serializer_class = ContractAttachmentSerializer
    table_class = ContractAttachmentTable
    action_buttons = _ATTACHMENT_ACTIONS
    object_detail_content = ObjectDetailContent(panels=_ATTACHMENT_DETAIL_PANELS)
