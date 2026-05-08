"""UI viewsets for the contract-models plugin."""

from .assignment import ContractAssignmentUIViewSet
from .attachment import InvoiceAttachmentUIViewSet
from .contract import ContractUIViewSet
from .invoice import InvoiceUIViewSet
from .provider import ServiceProviderUIViewSet

__all__ = [
    "ContractAssignmentUIViewSet",
    "ContractUIViewSet",
    "InvoiceAttachmentUIViewSet",
    "InvoiceUIViewSet",
    "ServiceProviderUIViewSet",
]
