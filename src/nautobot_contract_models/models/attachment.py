"""InvoiceAttachment — a file attached to an Invoice (typically a PDF)."""

import os

from django.db import models
from nautobot.core.models.generics import PrimaryModel


class InvoiceAttachment(PrimaryModel):
    """A single file uploaded against an :class:`Invoice`.

    The motivating use case: vendors send invoices as PDFs. Operators want to
    attach the actual PDF to the database row so future-them (or auditors)
    can see what the original looked like, not just the typed-in numbers.

    Files are stored under Nautobot's ``MEDIA_ROOT`` at
    ``invoice_attachments/YYYY/MM/<filename>`` and served at
    ``/media/invoice_attachments/...``. Nautobot's stack already volume-mounts
    ``/opt/nautobot/media/`` for persistence and exposes ``/media/`` via the
    web container — no extra configuration required.

    v1 keeps the model intentionally focused: attachments belong to *invoices*
    only. If operators later want to attach signed-contract PDFs or vendor
    quotes to Contracts, the cleanest path is a sibling ``ContractAttachment``
    model rather than a generic GFK — separate concerns, separate access
    controls, separate retention policies.
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
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional human-readable label (e.g. 'original vendor PDF', 'wire confirmation').",
    )

    natural_key_field_names = ["invoice", "file"]

    class Meta:
        """Model metadata."""

        ordering = ["-created", "file"]

    def __str__(self):
        """Render as the basename of the file plus the invoice number."""
        return f"{self.filename} ({self.invoice.invoice_number})"

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
