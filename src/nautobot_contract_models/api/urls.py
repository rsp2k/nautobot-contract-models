"""REST API URL routing for the contract-models plugin.

This file is more load-bearing than its size suggests: even before the API is
intentionally consumed, Nautobot's *post-save signal* uses the configured
serializer to snapshot a saved object into a ChangeLog entry. That snapshot
walks every hyperlinked field on the serializer and reverses the API URL —
so missing API routes will 500 the UI's create / edit / delete operations,
not just curl-against-the-API workflows.

Phase 4 (per PLAN.md) layers on serializer refinements, nested-relationship
handling, and richer API tests; the wiring here is the minimum needed to
keep the UI's mutating operations from failing during signal dispatch.
"""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_contract_models.views import (
    ContractAssignmentUIViewSet,
    ContractAttachmentUIViewSet,
    ContractUIViewSet,
    InvoiceAttachmentUIViewSet,
    InvoiceUIViewSet,
    ServiceProviderUIViewSet,
)

router = OrderedDefaultRouter()
router.register("service-providers", ServiceProviderUIViewSet)
router.register("contracts", ContractUIViewSet)
router.register("contract-attachments", ContractAttachmentUIViewSet)
router.register("invoices", InvoiceUIViewSet)
router.register("invoice-attachments", InvoiceAttachmentUIViewSet)
router.register("contract-assignments", ContractAssignmentUIViewSet)

app_name = "nautobot_contract_models-api"
urlpatterns = router.urls
