"""Tables for :class:`InvoiceAttachment`."""

import django_tables2 as tables
from django.utils.html import format_html
from nautobot.apps.tables import BaseTable, ButtonsColumn, ToggleColumn

from nautobot_contract_models.models import InvoiceAttachment


class InvoiceAttachmentTable(BaseTable):
    """List-view table for :class:`InvoiceAttachment`."""

    pk = ToggleColumn()
    filename = tables.Column(verbose_name="File", empty_values=())
    invoice = tables.LinkColumn()
    description = tables.Column()
    size_bytes = tables.Column(verbose_name="Size")
    created = tables.Column(verbose_name="Uploaded")
    actions = ButtonsColumn(InvoiceAttachment)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = InvoiceAttachment
        fields = ("pk", "filename", "invoice", "description", "size_bytes", "created", "actions")
        default_columns = ("pk", "filename", "invoice", "description", "size_bytes", "created", "actions")

    def render_filename(self, record):
        """Render the filename as a download link to the actual file."""
        if not record.file:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', record.file.url, record.filename)

    def render_size_bytes(self, record):
        """Render the file size in human-readable units (B / KB / MB)."""
        size = record.size_bytes
        if size is None:
            return "—"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
            size /= 1024
        return f"{size:.1f} GB"
