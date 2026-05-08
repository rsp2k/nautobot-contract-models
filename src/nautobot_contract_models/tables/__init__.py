"""django-tables2 tables for list views."""

from .assignment import ContractAssignmentTable
from .contract import ContractTable
from .invoice import InvoiceTable
from .provider import ServiceProviderTable

__all__ = [
    "ContractAssignmentTable",
    "ContractTable",
    "InvoiceTable",
    "ServiceProviderTable",
]
