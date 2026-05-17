"""Django ORM models for the contract-models plugin.

Public model surface:

- :class:`ServiceProvider` — the vendor / counterparty
- :class:`Contract` — the master agreement
- :class:`Invoice` — one billing line on a contract
- :class:`ContractAssignment` — generic-FK link between a Contract and any
  Nautobot object (Device, Circuit, VirtualMachine, …)
"""

from .access_token import ICalAccessToken
from .assignment import ContractAssignment
from .attachment import ContractAttachment, InvoiceAttachment
from .contract import Contract
from .coverage_snapshot import CoverageSnapshot
from .invoice import Invoice
from .provider import ServiceProvider
from .snapshot import CostSnapshot

__all__ = [
    "Contract",
    "ContractAssignment",
    "ContractAttachment",
    "CostSnapshot",
    "CoverageSnapshot",
    "ICalAccessToken",
    "Invoice",
    "InvoiceAttachment",
    "ServiceProvider",
]
