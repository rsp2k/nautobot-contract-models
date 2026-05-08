"""Tables for :class:`Contract`."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, StatusTableMixin, TagColumn, ToggleColumn

from nautobot_contract_models.models import Contract


class ContractTable(StatusTableMixin, BaseTable):
    """List-view table for :class:`Contract`.

    Columns are deliberately ordered for the renewals use case: end_date
    sits next to the status badge so an operator scanning the list can spot
    "Active but expiring soon" rows immediately.
    """

    pk = ToggleColumn()
    name = tables.LinkColumn()
    provider = tables.LinkColumn()
    tenant = tables.LinkColumn()
    end_date = tables.Column()
    start_date = tables.Column()
    recurring_cost = tables.Column()
    one_time_cost = tables.Column()
    currency = tables.Column()
    invoice_count = tables.Column(verbose_name="Invoices", accessor="invoices.count")
    assignment_count = tables.Column(verbose_name="Coverage", accessor="assignments.count")
    tags = TagColumn(url_name="plugins:nautobot_contract_models:contract_list")
    actions = ButtonsColumn(Contract)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = Contract
        fields = (
            "pk",
            "name",
            "contract_number",
            "provider",
            "tenant",
            "status",
            "start_date",
            "end_date",
            "recurring_cost",
            "one_time_cost",
            "currency",
            "invoice_count",
            "assignment_count",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "provider",
            "status",
            "end_date",
            "recurring_cost",
            "currency",
            "actions",
        )
