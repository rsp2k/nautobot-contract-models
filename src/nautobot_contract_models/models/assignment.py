"""ContractAssignment — generic-FK link between a Contract and any Nautobot object."""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class ContractAssignment(PrimaryModel):
    """Link a :class:`Contract` to *any* Nautobot object that has a UUID PK.

    Why generic FK rather than a typed M2M?
        We want one model to handle Contract-to-Device, Contract-to-Circuit,
        Contract-to-VirtualMachine, Contract-to-PowerFeed, etc. without a
        per-target-type table. Django's ContentType + GenericForeignKey gives
        us that. Operators can attach a Contract to anything in the Nautobot
        ORM — we don't have to enumerate the supported targets up front.

    Subclasses :class:`PrimaryModel` (matching Nautobot's own
    :class:`ContactAssociation`, which is the canonical GFK-link model). The
    full PrimaryModel surface — ChangeLog, custom fields, tags, Relationships,
    dynamic groups — applies. ChangeLog in particular matters: operators want
    to see "who linked this Contract to that Device, and when".

    Phase-2's earlier choice of ``BaseModel`` was wrong for this reason:
    ``NautobotModelForm`` expects ``RelationshipModelMixin`` on the model
    (which BaseModel doesn't include), so the create form 500s on
    ``instance.get_relationships()``. Promoting to PrimaryModel fixes the
    immediate bug AND aligns with how Nautobot itself models GFK links.
    """

    contract = models.ForeignKey(
        to="nautobot_contract_models.Contract",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="ContentType of the target object.",
    )
    object_id = models.UUIDField(help_text="UUID PK of the target object — every Nautobot model uses UUID PKs.")
    object = GenericForeignKey("content_type", "object_id")

    # --- Phase 7 per-assignment scope ---
    coverage_start = models.DateField(
        null=True,
        blank=True,
        help_text="When coverage of this target begins. Null = follows the contract's start_date.",
    )
    coverage_end = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "When coverage of this target ends. Null = follows the contract's end_date. "
            "Useful for mid-term additions/removals."
        ),
    )
    scope_notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional scope qualifier (e.g. 'chassis only, not modules'; 'firmware updates excluded').",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=(
            "When the same target is covered by multiple contracts, this flag picks "
            "the primary one for display / on-call routing."
        ),
    )
    # --- end Phase 7 ---

    class Meta:
        """Model metadata."""

        ordering = ["contract", "content_type", "object_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "content_type", "object_id"],
                name="nbcm_assignment_unique_target",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        """Render as ``<contract> -> <target>``; degrade gracefully if the GFK target is missing."""
        target = self.object if self.object_id else None
        return f"{self.contract.name} -> {target or 'unresolved'}"
