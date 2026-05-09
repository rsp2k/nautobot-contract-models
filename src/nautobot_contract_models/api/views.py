"""DRF viewsets for the contract-models REST API.

These are separate from the UI viewsets in ``nautobot_contract_models/views/``
on purpose: ``NautobotUIViewSet`` expects browser sessions and CSRF, so
registering it in ``api/urls.py`` would 403 every external API consumer
(curl, scripts, integrations). The ``NautobotModelViewSet`` base used here
is the API-tuned counterpart — token auth works, JSON content negotiation
works, no CSRF requirement.

The querysets here mirror the UI viewsets' querysets (same `select_related`
+ `count_related` annotations) so API responses include the same per-row
count fields the UI tables show. Phase 4 deliberately keeps the two
queryset definitions side-by-side rather than refactoring to a shared
helper — splitting them by axis (UI vs. API) makes per-surface tuning
(e.g. UI-only sort hints) cleaner later.
"""

from nautobot.apps.api import NautobotModelViewSet
from nautobot.core.models.querysets import count_related

from nautobot_contract_models.api.serializers import (
    ContractAssignmentSerializer,
    ContractAttachmentSerializer,
    ContractSerializer,
    InvoiceAttachmentSerializer,
    InvoiceSerializer,
    ServiceProviderSerializer,
)
from nautobot_contract_models.filters import (
    ContractAssignmentFilterSet,
    ContractAttachmentFilterSet,
    ContractFilterSet,
    InvoiceAttachmentFilterSet,
    InvoiceFilterSet,
    ServiceProviderFilterSet,
)
from nautobot_contract_models.models import (
    Contract,
    ContractAssignment,
    ContractAttachment,
    Invoice,
    InvoiceAttachment,
    ServiceProvider,
)


class ServiceProviderAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`ServiceProvider`."""

    queryset = ServiceProvider.objects.annotate(contract_count=count_related(Contract, "provider"))
    serializer_class = ServiceProviderSerializer
    filterset_class = ServiceProviderFilterSet


class ContractAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`Contract`."""

    queryset = Contract.objects.select_related("provider", "tenant", "status").annotate(
        invoice_count=count_related(Invoice, "contract"),
        assignment_count=count_related(ContractAssignment, "contract"),
        attachment_count=count_related(ContractAttachment, "contract"),
    )
    serializer_class = ContractSerializer
    filterset_class = ContractFilterSet


class InvoiceAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`Invoice`."""

    queryset = Invoice.objects.select_related("contract", "status").annotate(
        attachment_count=count_related(InvoiceAttachment, "invoice"),
    )
    serializer_class = InvoiceSerializer
    filterset_class = InvoiceFilterSet


class ContractAssignmentAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`ContractAssignment`."""

    queryset = ContractAssignment.objects.select_related("contract", "content_type")
    serializer_class = ContractAssignmentSerializer
    filterset_class = ContractAssignmentFilterSet


class InvoiceAttachmentAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`InvoiceAttachment`."""

    queryset = InvoiceAttachment.objects.select_related("invoice")
    serializer_class = InvoiceAttachmentSerializer
    filterset_class = InvoiceAttachmentFilterSet


class ContractAttachmentAPIViewSet(NautobotModelViewSet):
    """REST API for :class:`ContractAttachment`."""

    queryset = ContractAttachment.objects.select_related("contract")
    serializer_class = ContractAttachmentSerializer
    filterset_class = ContractAttachmentFilterSet
