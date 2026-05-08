"""DRF serializers for the contract-models plugin.

Phase 3 needs these only because :class:`NautobotUIViewSet` requires a
``serializer_class`` to instantiate. They're minimal — Phase 4 (REST API)
adds nested-relationship handling, custom validation, and richer field
shaping. For now ``fields = "__all__"`` produces a working JSON
representation that the UI views can lean on.
"""

from nautobot.apps.api import NautobotModelSerializer

from nautobot_contract_models.models import (
    Contract,
    ContractAssignment,
    Invoice,
    ServiceProvider,
)


class ServiceProviderSerializer(NautobotModelSerializer):
    """Serializer for :class:`ServiceProvider`."""

    class Meta:
        """Meta."""

        model = ServiceProvider
        fields = "__all__"


class ContractSerializer(NautobotModelSerializer):
    """Serializer for :class:`Contract`."""

    class Meta:
        """Meta."""

        model = Contract
        fields = "__all__"


class InvoiceSerializer(NautobotModelSerializer):
    """Serializer for :class:`Invoice`."""

    class Meta:
        """Meta."""

        model = Invoice
        fields = "__all__"


class ContractAssignmentSerializer(NautobotModelSerializer):
    """Serializer for :class:`ContractAssignment`.

    Note: ``object`` is a GenericForeignKey, not a regular field — DRF will
    serialize it as the target's URL via ``content_type`` + ``object_id``.
    Phase 4 may add a custom representation that resolves the target object's
    name for display.
    """

    class Meta:
        """Meta."""

        model = ContractAssignment
        fields = "__all__"
