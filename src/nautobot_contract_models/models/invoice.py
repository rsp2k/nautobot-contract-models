"""Invoice — a single billing line belonging to a Contract."""

from decimal import Decimal

from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.models.statuses import StatusField
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Invoice(PrimaryModel):
    """One invoice / billing line belonging to a Contract.

    Granularity: one row = one billing period. v1 doesn't model line-item
    breakdowns within an invoice — if an operator needs that, they add custom
    fields or build their own model.
    """

    contract = models.ForeignKey(
        to="nautobot_contract_models.Contract",
        on_delete=models.CASCADE,
        related_name="invoices",
        help_text="Owning contract. CASCADE — invoices can't exist orphaned from a contract.",
    )
    invoice_number = models.CharField(
        max_length=100,
        help_text="Vendor-supplied invoice number (must be unique within the owning contract).",
    )
    period_start = models.DateField(help_text="First day of the billing period this invoice covers.")
    period_end = models.DateField(help_text="Last day of the billing period this invoice covers.")
    invoice_date = models.DateField(help_text="Date the invoice was issued.")
    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the invoice was paid. Null while still outstanding.",
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO 4217 currency code. Should match the parent Contract; "
        "kept as a field rather than a property so currency conversions over "
        "time can be modeled if needed.",
    )
    # related_name namespace-prefixed defensively, matching Contract.status —
    # see contract.py for the collision rationale. DLC has no Invoice equivalent
    # today but other plugins may.
    status = StatusField(blank=False, null=False, related_name="contract_models_invoices")
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        """Model metadata."""

        ordering = ["-invoice_date", "invoice_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "invoice_number"],
                name="nbcm_invoice_unique_per_contract",
            ),
            models.CheckConstraint(
                condition=models.Q(period_end__gte=models.F("period_start")),
                name="nbcm_invoice_period_end_after_start",
            ),
        ]

    def __str__(self):
        """Render as ``<invoice_number> on <contract>``."""
        return f"{self.invoice_number} on {self.contract.name}"

    @property
    def is_paid(self):
        """True once a paid_date has been recorded."""
        return self.paid_date is not None
