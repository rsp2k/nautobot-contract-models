"""UI viewset for :class:`ContractAssignment`."""

from nautobot.apps.views import NautobotUIViewSet

from nautobot_contract_models.api.serializers import ContractAssignmentSerializer
from nautobot_contract_models.filters import ContractAssignmentFilterSet
from nautobot_contract_models.forms import ContractAssignmentFilterForm, ContractAssignmentForm
from nautobot_contract_models.models import ContractAssignment
from nautobot_contract_models.tables import ContractAssignmentTable


class ContractAssignmentUIViewSet(NautobotUIViewSet):
    """List / detail / create / edit / delete views for :class:`ContractAssignment`.

    No bulk-edit form: the model has only three meaningful fields and bulk
    editing assignments rarely makes sense (each row points at a different
    target). Bulk delete still works via the default action_buttons machinery.
    """

    filterset_class = ContractAssignmentFilterSet
    filterset_form_class = ContractAssignmentFilterForm
    form_class = ContractAssignmentForm
    queryset = ContractAssignment.objects.select_related("contract", "content_type")
    serializer_class = ContractAssignmentSerializer
    table_class = ContractAssignmentTable
    # Default action_buttons include "import" which doesn't make sense for an
    # assignment row (you can't paste in a CSV of UUIDs to bulk-link). Drop it.
    action_buttons = ("add",)
