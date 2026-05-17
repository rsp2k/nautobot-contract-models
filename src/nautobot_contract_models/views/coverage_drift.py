"""Coverage Drift report view — Phase 20.

Diffs two `CoverageSnapshot` row sets N days apart and surfaces:

- **Lost coverage** — devices that were covered on the baseline date and
  are NOT covered today. Operational regression signal.
- **Newly covered** — inverse. Sanity check that newly-signed contracts
  landed against the right devices.

Window is configurable via ``?days=N`` query param (default 30, capped at
365). If no historical snapshot rows exist for the baseline date, we
render an empty-state message pointing operators at the
``CoverageSnapshotJob`` so they know how to populate the table.
"""

from datetime import date, timedelta

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from nautobot_contract_models.models import CoverageSnapshot


class ContractCoverageDriftView(PermissionRequiredMixin, TemplateView):
    """Render the coverage-drift comparison page."""

    template_name = "nautobot_contract_models/coverage_drift.html"
    permission_required = "nautobot_contract_models.view_contract"

    def get_context_data(self, **kwargs):
        """Build the drift comparison context — lost + newly-covered devices."""
        ctx = super().get_context_data(**kwargs)
        try:
            days = max(1, min(365, int(self.request.GET.get("days", 30))))
        except (TypeError, ValueError):
            days = 30

        today = date.today()
        baseline = today - timedelta(days=days)

        # Find the snapshot date NEAR `baseline` — exact-date matches are rare
        # because operators schedule the job weekly, not daily. Use the most
        # recent snapshot ON OR BEFORE the baseline so we always compare
        # to "the most relevant historical state".
        baseline_actual = (
            CoverageSnapshot.objects.filter(snapshot_date__lte=baseline)
            .order_by("-snapshot_date")
            .values_list("snapshot_date", flat=True)
            .first()
        )
        latest_actual = (
            CoverageSnapshot.objects.filter(snapshot_date__lte=today)
            .order_by("-snapshot_date")
            .values_list("snapshot_date", flat=True)
            .first()
        )

        rows_lost = []
        rows_newly_covered = []
        baseline_count = 0
        latest_count = 0

        if baseline_actual and latest_actual and baseline_actual != latest_actual:
            baseline_rows = {
                s.device_id: s.was_covered
                for s in CoverageSnapshot.objects.filter(snapshot_date=baseline_actual).select_related("device")
            }
            latest_qs = CoverageSnapshot.objects.filter(snapshot_date=latest_actual).select_related(
                "device", "device__location", "device__tenant"
            )
            baseline_count = len(baseline_rows)
            latest_count = latest_qs.count()
            for snap in latest_qs:
                prev = baseline_rows.get(snap.device_id)
                if prev is None:
                    # Device wasn't in the baseline snapshot — likely a
                    # newly-added device. Don't count as drift; the operator
                    # would expect new devices to start uncovered until
                    # explicitly assigned.
                    continue
                if prev and not snap.was_covered:
                    rows_lost.append(snap)
                elif not prev and snap.was_covered:
                    rows_newly_covered.append(snap)

        ctx["window_options"] = [7, 30, 90, 180, 365]
        ctx["days"] = days
        ctx["today"] = today
        ctx["baseline"] = baseline
        ctx["baseline_actual"] = baseline_actual
        ctx["latest_actual"] = latest_actual
        ctx["baseline_count"] = baseline_count
        ctx["latest_count"] = latest_count
        ctx["rows_lost"] = rows_lost
        ctx["rows_newly_covered"] = rows_newly_covered
        ctx["has_history"] = baseline_actual is not None and latest_actual is not None
        return ctx
