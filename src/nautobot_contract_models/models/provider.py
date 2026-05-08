"""ServiceProvider — the vendor / counterparty side of a Contract."""

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
class ServiceProvider(PrimaryModel):
    """A vendor or counterparty that provides services under one or more Contracts.

    Use Nautobot's Contact framework (``associated_contacts``) to track named
    individuals (account manager, support rep, billing contact). The fields
    here are *vendor-level* — the portal you log into, the main support line —
    not contact-of-contact metadata.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Vendor display name (must be unique across the install).",
    )
    account_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Customer / account number assigned by the vendor.",
    )
    portal_url = models.URLField(
        blank=True,
        help_text="URL of the vendor's customer portal where you log in to manage the account.",
    )
    support_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Primary support phone number (free-form to accommodate international formats).",
    )
    description = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        """Model metadata."""

        verbose_name = "Service Provider"
        verbose_name_plural = "Service Providers"
        ordering = ["name"]

    def __str__(self):
        """Render as the vendor's display name."""
        return self.name
