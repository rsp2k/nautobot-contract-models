"""Tables for :class:`ContractAssignment`."""

import django_tables2 as tables
from nautobot.apps.tables import BaseTable, ButtonsColumn, ToggleColumn

from nautobot_contract_models.models import ContractAssignment


class ContractAssignmentTable(BaseTable):
    """List-view table for :class:`ContractAssignment`."""

    pk = ToggleColumn()
    contract = tables.LinkColumn()
    content_type = tables.Column(verbose_name="Target Type")
    object = tables.Column(verbose_name="Target", empty_values=(), orderable=False)
    actions = ButtonsColumn(ContractAssignment)

    class Meta(BaseTable.Meta):
        """Meta."""

        model = ContractAssignment
        fields = ("pk", "contract", "content_type", "object", "actions")
        default_columns = ("pk", "contract", "content_type", "object", "actions")

    def render_object(self, record):
        """Render the GenericForeignKey target (degrades gracefully if dangling)."""
        target = record.object if record.object_id else None
        return str(target) if target else "—"
