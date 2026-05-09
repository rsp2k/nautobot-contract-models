"""Attachment models — files attached to Invoices and Contracts (typically PDFs).

Two near-identical sibling models, one per parent type. Splitting (rather than
one generic GFK Attachment) follows netbox-contract's convention and keeps
retention / access-control reasoning per-parent simple. If a third type ever
needs attachments, copy-paste the pattern; if four or more accumulate, that's
the trigger to refactor to a generic GFK model.
"""

import os

from django.db import models
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features

_ATTACHMENT_EXTRAS = (
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)


class _AttachmentBase(PrimaryModel):
    """Shared file/description fields and helpers for the attachment models.

    Abstract — subclasses add the actual parent FK. The shared fields and
    helpers keep the table layout and the per-cell rendering identical
    across the two attachment types so operators see consistent UX.
    """

    file = models.FileField(
        help_text="The uploaded file. Typically a PDF, but any file type is allowed.",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional human-readable label (e.g. 'original vendor PDF', 'wire confirmation').",
    )

    class Meta:
        """Abstract — concrete subclasses inherit field config + Meta defaults."""

        abstract = True
        ordering = ["-created", "file"]

    @property
    def filename(self):
        """Return just the basename of the stored file (without the upload-path prefix)."""
        return os.path.basename(self.file.name) if self.file else ""

    @property
    def size_bytes(self):
        """File size in bytes, or None if the file is missing on disk."""
        try:
            return self.file.size
        except (FileNotFoundError, ValueError, OSError):
            return None


@extras_features(*_ATTACHMENT_EXTRAS)
class InvoiceAttachment(_AttachmentBase):
    """A single file uploaded against an :class:`Invoice`.

    The motivating use case: vendors send invoices as PDFs. Operators want to
    attach the actual PDF to the database row so future-them (or auditors)
    can see what the original looked like, not just the typed-in numbers.

    Files land at ``invoice_attachments/YYYY/MM/<filename>`` under Nautobot's
    ``MEDIA_ROOT`` and serve at ``/media/invoice_attachments/...``. The
    ``nautobot-media`` Docker volume persists them across restarts; production
    deployments need a separate backup strategy for that volume since DB
    dumps don't include media files.
    """

    invoice = models.ForeignKey(
        to="nautobot_contract_models.Invoice",
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text="Owning invoice. CASCADE — attachments can't outlive their invoice.",
    )
    file = models.FileField(
        upload_to="invoice_attachments/%Y/%m/",
        help_text="The uploaded file. Typically a PDF, but any file type is allowed.",
    )

    natural_key_field_names = ["invoice", "file"]

    class Meta(_AttachmentBase.Meta):
        """Concrete metadata."""

        abstract = False

    def __str__(self):
        """Render as ``<filename> (<invoice_number>)``."""
        return f"{self.filename} ({self.invoice.invoice_number})"


@extras_features(*_ATTACHMENT_EXTRAS)
class ContractAttachment(_AttachmentBase):
    """A single file uploaded against a :class:`Contract`.

    Common contents: the signed contract PDF itself, vendor SOWs / proposals,
    renewal-letter scans, addenda. Operators usually upload one or two and
    reference them rarely — the typical access pattern is "I need to see the
    actual signed agreement".

    Files land at ``contract_attachments/YYYY/MM/<filename>``. Same volume,
    same backup discipline as :class:`InvoiceAttachment`.
    """

    contract = models.ForeignKey(
        to="nautobot_contract_models.Contract",
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text="Owning contract. CASCADE — attachments can't outlive their contract.",
    )
    file = models.FileField(
        upload_to="contract_attachments/%Y/%m/",
        help_text="The uploaded file. Typically a PDF, but any file type is allowed.",
    )

    natural_key_field_names = ["contract", "file"]

    class Meta(_AttachmentBase.Meta):
        """Concrete metadata."""

        abstract = False

    def __str__(self):
        """Render as ``<filename> (<contract_name>)``."""
        return f"{self.filename} ({self.contract.name})"
