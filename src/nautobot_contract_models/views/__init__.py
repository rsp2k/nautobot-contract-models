"""UI viewsets for the contract-models plugin."""

from .assignment import ContractAssignmentUIViewSet
from .attachment import ContractAttachmentUIViewSet, InvoiceAttachmentUIViewSet
from .calendar import ContractRenewalCalendarView
from .contract import ContractUIViewSet
from .invoice import InvoiceUIViewSet
from .provider import ServiceProviderUIViewSet

__all__ = [
    "ContractAssignmentUIViewSet",
    "ContractAttachmentUIViewSet",
    "ContractRenewalCalendarView",
    "ContractUIViewSet",
    "InvoiceAttachmentUIViewSet",
    "InvoiceUIViewSet",
    "ServiceProviderUIViewSet",
]
