"""Action Required view — contracts inside their notice window or imminent.

Phase 12 introduces this. Renders priority-bucketed contracts (URGENT,
WARNING, INFO) so operators have a single page that answers "what do I
need to do this week to avoid a renewal surprise?".

Lives under ``reports/`` rather than ``contracts/`` to dodge the
NautobotUIViewSetRouter's ``contracts/<uuid>/`` detail-route collision
— same lesson as the Renewal Calendar.
"""

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from nautobot_contract_models import priority


class ContractActionRequiredView(PermissionRequiredMixin, TemplateView):
    """List contracts that need operator attention, sorted by urgency."""

    template_name = "nautobot_contract_models/contract_action_required.html"
    permission_required = "nautobot_contract_models.view_contract"

    def get_context_data(self, **kwargs):
        """Bucket the priority rows so the template can render per-tier sections."""
        ctx = super().get_context_data(**kwargs)

        try:
            window_days = max(1, min(365, int(self.request.GET.get("window_days", 60))))
        except (TypeError, ValueError):
            window_days = 60

        rows = priority.contracts_needing_action(window_days=window_days)

        # Pre-bucket by tier so the template's three sections render cleanly.
        # We keep priority.contracts_needing_action's pre-sorted ordering
        # within each bucket.
        buckets = {priority.URGENT: [], priority.WARNING: [], priority.INFO: []}
        for contract, tier in rows:
            buckets[tier].append(contract)

        ctx["window_days"] = window_days
        ctx["urgent"] = buckets[priority.URGENT]
        ctx["warning"] = buckets[priority.WARNING]
        ctx["info"] = buckets[priority.INFO]
        ctx["total"] = sum(len(b) for b in buckets.values())
        return ctx
