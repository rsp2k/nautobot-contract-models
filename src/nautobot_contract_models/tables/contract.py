"""Tables for :class:`Contract`."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, StatusTableMixin, TagColumn, ToggleColumn

from nautobot_contract_models.cost import monthly_cost
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
    contract_type = tables.Column()
    coverage_hours = tables.Column()
    response_time = tables.Column()
    auto_renew = tables.BooleanColumn()
    recurring_cost = tables.Column()
    billing_period = tables.Column()
    # Computed: normalized monthly figure across mixed billing cadences. Not a
    # model field — django_tables2 renders it via render_monthly_cost below.
    monthly_cost = tables.Column(empty_values=(), verbose_name="Monthly", orderable=False)
    one_time_cost = tables.Column()
    currency = tables.Column()
    invoice_count = tables.Column(verbose_name="Invoices", accessor="invoices.count")
    assignment_count = tables.Column(verbose_name="Coverage", accessor="assignments.count")
    tags = TagColumn(url_name="plugins:nautobot_contract_models:contract_list")
    actions = ButtonsColumn(Contract)

    def render_monthly_cost(self, record):
        """Render the cost helper's normalized monthly figure with two decimals."""
        return f"{monthly_cost(record):.2f}"

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
            "contract_type",
            "coverage_hours",
            "response_time",
            "auto_renew",
            "start_date",
            "end_date",
            "recurring_cost",
            "billing_period",
            "monthly_cost",
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
            "contract_type",
            "end_date",
            "monthly_cost",
            "currency",
            "actions",
        )
