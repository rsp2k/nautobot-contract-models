"""ContractAssignment — generic-FK link between a Contract and any Nautobot object."""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from nautobot.core.models.generics import BaseModel


class ContractAssignment(BaseModel):
    """Link a :class:`Contract` to *any* Nautobot object that has a UUID PK.

    Why generic FK rather than a typed M2M?
        We want one model to handle Contract-to-Device, Contract-to-Circuit,
        Contract-to-VirtualMachine, Contract-to-PowerFeed, etc. without a
        per-target-type table. Django's ContentType + GenericForeignKey gives
        us that. Operators can attach a Contract to anything in the Nautobot
        ORM — we don't have to enumerate the supported targets up front.

    Subclasses :class:`BaseModel` (not :class:`PrimaryModel`) on purpose: an
    assignment row is a *link*, not a primary record. It doesn't get its own
    changelog entries — changes to the assignment are reflected as changelog
    entries on the contract and the target object instead.
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
