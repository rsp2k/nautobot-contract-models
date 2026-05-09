"""DRF serializers for the contract-models plugin.

Each serializer mixes :class:`TaggedModelSerializerMixin` so the ``tags``
field renders as a flat list of tag names rather than the M2M-URL noise the
default ``ModelSerializer`` produces. Parent-side serializers expose
read-only count annotations (``contract_count``, ``invoice_count``, etc.)
for at-a-glance API dashboards — populated by the corresponding viewset's
queryset annotation.

Nested expansion of FK fields (``provider`` → full ServiceProvider blob) is
not declared at class level — Nautobot's framework supports it via the
``?depth=N`` query parameter at request time. Consumers who need flat
hyperlinks omit it; consumers who want one-call workflows pass ``?depth=1``.
"""

from nautobot.apps.api import NautobotModelSerializer
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from rest_framework import serializers

from nautobot_contract_models.models import (
    Contract,
    ContractAssignment,
    ContractAttachment,
    CostSnapshot,
    Invoice,
    InvoiceAttachment,
    ServiceProvider,
)


class ServiceProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`ServiceProvider` with contract count annotation."""

    contract_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta."""

        model = ServiceProvider
        fields = "__all__"


class ContractSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`Contract` with invoice / assignment / attachment counts."""

    invoice_count = serializers.IntegerField(read_only=True)
    assignment_count = serializers.IntegerField(read_only=True)
    attachment_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta."""

        model = Contract
        fields = "__all__"


class InvoiceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`Invoice` with attachment count."""

    attachment_count = serializers.IntegerField(read_only=True)

    class Meta:
        """Meta."""

        model = Invoice
        fields = "__all__"


class ContractAssignmentSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`ContractAssignment`.

    The ``object`` GenericForeignKey is not a regular field — DRF surfaces
    it as the target's URL via ``content_type`` + ``object_id``. Consumers
    who want the resolved target (Device name, Circuit cid, etc.) call
    ``GET /api/<target-app>/<target-model>/<object_id>/`` themselves.
    """

    class Meta:
        """Meta."""

        model = ContractAssignment
        fields = "__all__"


class InvoiceAttachmentSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`InvoiceAttachment`."""

    class Meta:
        """Meta."""

        model = InvoiceAttachment
        fields = "__all__"


class ContractAttachmentSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    """Serializer for :class:`ContractAttachment`."""

    class Meta:
        """Meta."""

        model = ContractAttachment
        fields = "__all__"


class CostSnapshotSerializer(NautobotModelSerializer):
    """Serializer for :class:`CostSnapshot` — read-only telemetry, no Tags mixin.

    Snapshots are write-once aggregates; they don't support tags or
    attachments. The viewset paired with this serializer also strips
    write methods (POST/PATCH/DELETE) so external tools can't rewrite
    history.
    """

    class Meta:
        """Meta."""

        model = CostSnapshot
        fields = "__all__"
