"""Template extensions — inject our panels into Nautobot's own object detail pages.

Phase 20 introduces ``DeviceActiveContracts``: a side panel on every Device
detail page that lists the Contracts covering that Device. Coverage is
**transitive** — the same walk used by ``helpers.has_active_coverage`` and
the Coverage Gaps home panel. A Device covered by its Tenant or Location
shows that contract too, with a "via Tenant: …" / "via Location: …" source
label so operators know whether the coverage is direct or inherited.

The pattern mirrors DLM's own ``DeviceContractLCM`` (at
``nautobot_device_lifecycle_mgmt/template_content.py:155-189``): subclass
``TemplateExtension``, set ``model = "dcim.device"``, override
``right_page()``. Registration happens via a module-level
``template_extensions`` list; Nautobot auto-discovers it.
"""

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.plugins import TemplateExtension

from nautobot_contract_models.helpers import coverage_assignments


def _source_label(assignment, device):
    """Render a human description of how this assignment covers the device.

    Direct device assignment → "direct".
    Via Tenant/Location/Rack/parent-device → "via Tenant: ACME Corp" etc.
    Used in the right_page panel's Source column.
    """
    device_ct = ContentType.objects.get_for_model(type(device))
    if assignment.content_type_id == device_ct.id and assignment.object_id == device.pk:
        return "direct"
    # The assignment's content_type tells us what kind of ancestor it's bound to.
    kind = assignment.content_type.model_class().__name__
    target = assignment.object  # GenericForeignKey lookup; one row, already prefetched at the ORM level
    if target is None:
        return f"via {kind}: <unresolved>"
    name = getattr(target, "name", str(target))
    return f"via {kind}: {name}"


class DeviceActiveContracts(TemplateExtension):  # pylint: disable=abstract-method
    """Right-side panel listing active Contracts covering this Device (direct + transitive)."""

    model = "dcim.device"

    def __init__(self, context):
        """Pre-compute the coverage list so right_page() is cheap."""
        super().__init__(context)
        device = self.context["object"]
        # Up to 10 active assignments. Operators with more should drill into
        # the contracts list filtered by device — the panel is a peek, not
        # the canonical surface.
        assignments = coverage_assignments(device)[:10]
        self.rows = [
            {
                "assignment": a,
                "contract": a.contract,
                "source_label": _source_label(a, device),
            }
            for a in assignments
        ]
        self.device = device

    def right_page(self):
        """Render the panel HTML."""
        return self.render(
            "nautobot_contract_models/inc/device_active_contracts.html",
            extra_context={"rows": self.rows, "device": self.device},
        )


template_extensions = [DeviceActiveContracts]
