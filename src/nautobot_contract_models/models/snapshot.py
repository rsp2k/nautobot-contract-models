"""CostSnapshot — point-in-time aggregate of fleet contract costs.

Phase 13 introduces this. Each row captures the fleet-wide burn rate,
90-day renewal forecast, and contract count *for one currency on one
date*. Snapshots are write-once telemetry: there's no "edit a snapshot"
workflow, and we never delete a snapshot when a contract changes — the
historical value is "what we believed on date X".

Why no FK to Contract:
    A snapshot is a fleet aggregate, not a per-contract row. An FK
    would mean deleting a contract destroys the historical record of
    its spend, which is exactly wrong. Snapshots are immutable
    historical facts, decoupled from current Contract state.

Why one row per (date, currency):
    Querying "USD trend over 12 weeks" should be an ORM filter, not a
    JSON path expression. The unique constraint on (snapshot_date,
    currency) also prevents double-snapshotting the same day if an
    operator runs the Job twice.

Why BaseModel rather than PrimaryModel:
    Snapshots don't need ChangeLog / Relationships / Tags / dynamic
    groups. Operators don't tag a snapshot or relate it to a Device.
    BaseModel gives us the UUID PK + timestamps + natural-key machinery,
    which is the minimum useful surface.
"""

from decimal import Decimal

from django.db import models
from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features


@extras_features("graphql")
class CostSnapshot(BaseModel):
    """One per-currency aggregate of fleet contract costs on one date."""

    snapshot_date = models.DateField(
        help_text="The date this snapshot represents. Multiple currencies on the same date = multiple rows.",
    )
    currency = models.CharField(
        max_length=3,
        help_text="ISO 4217 currency code. Snapshots are per-currency; we never sum across currencies.",
    )
    monthly_burn = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sum of monthly_cost across active contracts in this currency on snapshot_date.",
    )
    renewal_90d = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total renewal cost in the 90-day forward window from snapshot_date, this currency.",
    )
    active_contract_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of active contracts in this currency on snapshot_date.",
    )
    coverage_gap_count = models.PositiveIntegerField(
        default=0,
        null=True,
        blank=True,
        help_text=(
            "Devices with no direct contract assignment as of snapshot_date. "
            "Stored on the first per-date snapshot only — null on others — "
            "since the gap count is currency-agnostic."
        ),
    )

    natural_key_field_names = ["snapshot_date", "currency"]

    class Meta:
        """Model metadata."""

        ordering = ["-snapshot_date", "currency"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "currency"],
                name="nbcm_costsnapshot_unique_per_date_currency",
            ),
        ]
        indexes = [
            models.Index(fields=["-snapshot_date", "currency"]),
        ]

    def __str__(self):
        """Render as ``YYYY-MM-DD CUR``."""
        return f"{self.snapshot_date} {self.currency}"
