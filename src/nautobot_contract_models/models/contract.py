"""Contract — the master vendor agreement, with dates, costs, and a Status."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.models.statuses import StatusField
from nautobot.extras.utils import extras_features

from nautobot_contract_models.choices import (
    ContractTypeChoices,
    CoverageHoursChoices,
    ResponseTimeChoices,
    RestorationTimeChoices,
)


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
class Contract(PrimaryModel):
    """A vendor agreement, with start/end dates, recurring + one-time costs, and a status.

    Attaches to one or more concrete Nautobot objects (Devices, Circuits,
    VirtualMachines, etc.) via :class:`ContractAssignment` — see that model's
    docstring for why we use a generic FK rather than a per-target M2M.
    """

    name = models.CharField(max_length=255)
    contract_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Vendor-supplied contract or master agreement number.",
    )
    provider = models.ForeignKey(
        to="nautobot_contract_models.ServiceProvider",
        on_delete=models.PROTECT,
        related_name="contracts",
        help_text="Counterparty on this agreement. PROTECT — can't delete a "
        "provider while contracts still reference it.",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.SET_NULL,
        related_name="contract_models_contracts",
        null=True,
        blank=True,
        help_text="Owning tenant. Nullable — a contract may apply globally to "
        "the operator's whole estate rather than to one tenant.",
    )
    status = StatusField(blank=False, null=False)
    start_date = models.DateField(help_text="When coverage starts.")
    end_date = models.DateField(help_text="When coverage ends (renewal target).")
    renewal_terms = models.CharField(
        max_length=255,
        blank=True,
        help_text="Free-form: e.g. 'Auto-renew unless cancelled 60d prior'.",
    )
    recurring_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Periodic cost (per the renewal cycle implied by the dates).",
    )
    one_time_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Setup / activation / migration fees that aren't recurring.",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO 4217 currency code (e.g. USD, EUR, GBP). v1 doesn't "
        "convert between currencies — totals across mixed-currency contracts "
        "are the operator's problem.",
    )
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    # --- Phase 7 SLA / contract-shape structure ---
    contract_type = models.CharField(
        max_length=30,
        choices=ContractTypeChoices,
        blank=True,
        help_text="Category of agreement (drives default renewal priority and dashboard grouping).",
    )
    coverage_hours = models.CharField(
        max_length=30,
        choices=CoverageHoursChoices,
        blank=True,
        help_text="When the vendor is contractually available to take a support call.",
    )
    response_time = models.CharField(
        max_length=30,
        choices=ResponseTimeChoices,
        blank=True,
        help_text="Vendor's contractual response-time SLA.",
    )
    restoration_time = models.CharField(
        max_length=30,
        choices=RestorationTimeChoices,
        blank=True,
        help_text="Vendor's contractual time-to-restore SLA. Distinct from response time.",
    )
    notice_period_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Days before end_date by which a cancellation notice must be served (e.g. 60). "
            "Used by the renewal Job to alert earlier."
        ),
    )
    auto_renew = models.BooleanField(
        default=False,
        help_text="Does this contract auto-renew if no notice is served? Affects renewal-Job urgency.",
    )
    term_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Original term length in months (12, 24, 36...). Null = perpetual or month-to-month.",
    )
    # --- end Phase 7 ---

    # Required by Nautobot's natural_slug / natural_key machinery (used by
    # detail views, REST API URL stability, and import/export matching).
    # Neither `name` nor `contract_number` is unique on its own (yearly
    # renewals reuse names; numbers are vendor-supplied and may collide
    # across providers), so we declare the (provider, name) pair as the
    # natural key — without imposing a DB-level UniqueConstraint that
    # would block legitimate duplicates. This is a Nautobot-level attribute,
    # NOT a Django Meta attribute (Django's Meta rejects unknown keys).
    natural_key_field_names = ["name", "provider"]

    class Meta:
        """Model metadata."""

        ordering = ["name", "-end_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="nbcm_contract_end_after_start",
            ),
        ]

    def __str__(self):
        """Render with the contract number when present."""
        if self.contract_number:
            return f"{self.name} ({self.contract_number})"
        return self.name

    @property
    def is_expired(self):
        """True if the contract's end_date has already passed."""
        return self.end_date < date.today()

    def is_expiring_within(self, days):
        """True if the contract expires within ``days`` from today (inclusive of today)."""
        today = date.today()
        return today <= self.end_date <= today + timedelta(days=days)
