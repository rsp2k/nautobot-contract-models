"""UI viewsets for the contract-models plugin."""

from .action_required import ContractActionRequiredView
from .assignment import ContractAssignmentUIViewSet
from .attachment import ContractAttachmentUIViewSet, InvoiceAttachmentUIViewSet
from .calendar import ContractRenewalCalendarView
from .contract import ContractUIViewSet
from .cost_history import ContractCostHistoryView
from .invoice import InvoiceUIViewSet
from .provider import ServiceProviderUIViewSet

__all__ = [
    "ContractActionRequiredView",
    "ContractAssignmentUIViewSet",
    "ContractAttachmentUIViewSet",
    "ContractCostHistoryView",
    "ContractRenewalCalendarView",
    "ContractUIViewSet",
    "InvoiceAttachmentUIViewSet",
    "InvoiceUIViewSet",
    "ServiceProviderUIViewSet",
]
