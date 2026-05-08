"""URL routing for the contract-models plugin.

The :class:`NautobotUIViewSetRouter` introspects each viewset and emits the
canonical URL patterns for list / detail / create / edit / delete / bulk-edit
/ bulk-delete / import / export, all named consistently as
``plugins:nautobot_contract_models:<model>_<action>`` (e.g.
``plugins:nautobot_contract_models:contract_list``). Tables and forms in this
plugin reference those name-strings.
"""

from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_contract_models.views import (
    ContractAssignmentUIViewSet,
    ContractAttachmentUIViewSet,
    ContractUIViewSet,
    InvoiceAttachmentUIViewSet,
    InvoiceUIViewSet,
    ServiceProviderUIViewSet,
)

router = NautobotUIViewSetRouter()
router.register("service-providers", ServiceProviderUIViewSet)
router.register("contracts", ContractUIViewSet)
router.register("contract-attachments", ContractAttachmentUIViewSet)
router.register("invoices", InvoiceUIViewSet)
router.register("invoice-attachments", InvoiceAttachmentUIViewSet)
router.register("contract-assignments", ContractAssignmentUIViewSet)

app_name = "nautobot_contract_models"
urlpatterns = router.urls
