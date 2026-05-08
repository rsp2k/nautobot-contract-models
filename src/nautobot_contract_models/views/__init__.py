"""UI viewsets for the contract-models plugin."""

from .assignment import ContractAssignmentUIViewSet
from .attachment import ContractAttachmentUIViewSet, InvoiceAttachmentUIViewSet
from .contract import ContractUIViewSet
from .invoice import InvoiceUIViewSet
from .provider import ServiceProviderUIViewSet

__all__ = [
    "ContractAssignmentUIViewSet",
    "ContractAttachmentUIViewSet",
    "ContractUIViewSet",
    "InvoiceAttachmentUIViewSet",
    "InvoiceUIViewSet",
    "ServiceProviderUIViewSet",
]
