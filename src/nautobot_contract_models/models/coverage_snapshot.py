"""CoverageSnapshot — point-in-time record of whether a Device had contract coverage.

Phase 20 introduces this. Each row captures whether a single Device was
under active contract coverage (direct OR transitive) on a given date. The
``CoverageSnapshotJob`` writes these rows weekly; the Coverage Drift view
diffs two snapshots N days apart to answer "which devices lost coverage?"

Why one row per (date, device):
    Operators want to investigate specific devices, not just aggregate
    counts. Storing per-device state enables drift reports that *name
    the devices that lost coverage*, not just "5 devices lost coverage".

Why BaseModel rather than PrimaryModel:
    Snapshots are internal telemetry. Operators don't tag a snapshot or
    relate it to a Contract; the snapshot describes one fact about one
    device on one date. BaseModel gives the UUID PK + timestamps we need.

Why CASCADE on device:
    A snapshot referring to a deleted device is uninteresting noise.
    Cascade-delete keeps the table clean.

Storage cost:
    52K rows/year for a 1000-device fleet snapshotted weekly. Comfortably
    within reasonable DB size for years before garbage-collection becomes
    necessary. If fleets push 10x+, a retention Job can be added without
    schema change.
"""

from django.db import models
from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features


@extras_features("graphql")
class CoverageSnapshot(BaseModel):
    """One per-device coverage state on one date. Idempotent via UniqueConstraint."""

    snapshot_date = models.DateField(
        help_text="The date this snapshot represents.",
    )
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="contract_models_coverage_snapshots",
        help_text="The device whose coverage state this row captures.",
    )
    was_covered = models.BooleanField(
        help_text=(
            "True if the device had any active ContractAssignment "
            "(direct or via Tenant/Location/Rack) on snapshot_date."
        ),
    )

    natural_key_field_names = ["snapshot_date", "device"]

    class Meta:
        """Model metadata."""

        ordering = ["-snapshot_date", "device"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot_date", "device"],
                name="nbcm_coveragesnapshot_unique_per_date_device",
            ),
        ]
        indexes = [
            models.Index(fields=["-snapshot_date", "was_covered"]),
        ]

    def __str__(self):
        """Render as ``YYYY-MM-DD device=name covered=True``."""
        return f"{self.snapshot_date} device={self.device.name} covered={self.was_covered}"
