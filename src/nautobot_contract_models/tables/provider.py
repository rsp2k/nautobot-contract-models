"""Tables for :class:`ServiceProvider`."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, TagColumn, ToggleColumn

from nautobot_contract_models.models import ServiceProvider


class ServiceProviderTable(BaseTable):
    """List-view table for :class:`ServiceProvider`."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    contract_count = tables.Column(verbose_name="Contracts", accessor="contracts.count")
    tags = TagColumn(url_name="plugins:nautobot_contract_models:serviceprovider_list")
    actions = ButtonsColumn(ServiceProvider)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = ServiceProvider
        fields = (
            "pk",
            "name",
            "account_number",
            "portal_url",
            "support_phone",
            "contract_count",
            "tags",
            "actions",
        )
        default_columns = ("pk", "name", "account_number", "support_phone", "contract_count", "actions")
