"""REST API URL routing for the contract-models plugin.

Registers :class:`NautobotModelViewSet` subclasses (not the UI viewsets):
the UI viewsets enforce browser-session conventions that 403 external API
consumers. Phase 3's earlier registration of UI viewsets here covered the
internal post_save changelog signal path, but real API workflows need this
clean separation.
"""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_contract_models.api.views import (
    ContractAPIViewSet,
    ContractAssignmentAPIViewSet,
    ContractAttachmentAPIViewSet,
    InvoiceAPIViewSet,
    InvoiceAttachmentAPIViewSet,
    ServiceProviderAPIViewSet,
)

router = OrderedDefaultRouter()
router.register("service-providers", ServiceProviderAPIViewSet)
router.register("contracts", ContractAPIViewSet)
router.register("contract-attachments", ContractAttachmentAPIViewSet)
router.register("invoices", InvoiceAPIViewSet)
router.register("invoice-attachments", InvoiceAttachmentAPIViewSet)
router.register("contract-assignments", ContractAssignmentAPIViewSet)

app_name = "nautobot_contract_models-api"
urlpatterns = router.urls
