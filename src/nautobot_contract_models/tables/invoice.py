"""Tables for :class:`Invoice`."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, BooleanColumn, ButtonsColumn, StatusTableMixin, TagColumn, ToggleColumn

from nautobot_contract_models.models import Invoice


class InvoiceTable(StatusTableMixin, BaseTable):
    """List-view table for :class:`Invoice`."""

    pk = ToggleColumn()
    invoice_number = tables.LinkColumn()
    contract = tables.LinkColumn()
    invoice_date = tables.Column()
    period_start = tables.Column()
    period_end = tables.Column()
    paid_date = tables.Column()
    is_paid = BooleanColumn(verbose_name="Paid")
    total_amount = tables.Column()
    currency = tables.Column()
    tags = TagColumn(url_name="plugins:nautobot_contract_models:invoice_list")
    actions = ButtonsColumn(Invoice)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = Invoice
        fields = (
            "pk",
            "invoice_number",
            "contract",
            "invoice_date",
            "period_start",
            "period_end",
            "paid_date",
            "is_paid",
            "total_amount",
            "currency",
            "status",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "invoice_number",
            "contract",
            "invoice_date",
            "total_amount",
            "currency",
            "is_paid",
            "status",
            "actions",
        )
