"""Cost History view — time-series line charts per currency.

Phase 13 introduces this. Reads CostSnapshot rows and renders one
line chart per metric (monthly burn, 90-day renewal forecast, active
contract count) with one line per currency. Inline SVG — no JS chart
library, no external dependency.

Operators schedule the ``Capture cost history snapshot`` Job to feed
this surface; on a fresh install with no snapshots, the view renders
an empty state pointing at the Job.
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from nautobot_contract_models import cost

# Single-hue ramp matching the rest of the cost UI; the operator's
# CLAUDE.md disallows purple. We pick amber / teal as the two base
# hues then cycle if more currencies appear.
_CURRENCY_HUES = [35, 190, 130, 270, 0]  # amber, teal, green, indigo, red — last as final fallback


class ContractCostHistoryView(PermissionRequiredMixin, TemplateView):
    """Render the cost-history page (three SVG line charts)."""

    template_name = "nautobot_contract_models/contract_cost_history.html"
    permission_required = "nautobot_contract_models.view_contract"

    def get_context_data(self, **kwargs):
        """Build per-metric series structures the template can iterate without doing math."""
        ctx = super().get_context_data(**kwargs)

        try:
            weeks = max(2, min(104, int(self.request.GET.get("weeks", 12))))
        except (TypeError, ValueError):
            weeks = 12

        snapshots = cost.history(weeks=weeks)

        if not snapshots:
            ctx["weeks"] = weeks
            ctx["empty"] = True
            return ctx

        # Group snapshots into per-currency series keyed by metric name.
        # series[metric][currency] = [(date, value), ...] sorted by date
        metric_keys = ("monthly_burn", "renewal_90d", "active_contract_count")
        series = {metric: defaultdict(list) for metric in metric_keys}
        for snap in snapshots:
            for metric in metric_keys:
                series[metric][snap.currency].append((snap.snapshot_date, getattr(snap, metric)))

        # Build per-metric chart blocks the template renders.
        # Each block has: title, unit, list of series dicts (currency, hue, points, path_d).
        currencies = sorted({snap.currency for snap in snapshots})
        currency_hues = {c: _CURRENCY_HUES[i % len(_CURRENCY_HUES)] for i, c in enumerate(currencies)}

        chart_w, chart_h = 600, 120
        x_pad, y_pad = 8, 8

        charts = []
        for metric, label, unit in (
            ("monthly_burn", "Monthly burn rate", "/mo"),
            ("renewal_90d", "90-day renewal forecast", " (renewal)"),
            ("active_contract_count", "Active contracts", " (count)"),
        ):
            metric_series = series[metric]
            # Find global x-range (date span) and y-range (max value).
            all_dates = sorted({d for points in metric_series.values() for d, _ in points})
            if not all_dates:
                charts.append({"label": label, "unit": unit, "series": [], "empty": True})
                continue
            date_min, date_max = all_dates[0], all_dates[-1]
            value_max = max(
                (Decimal(str(v)) for points in metric_series.values() for _, v in points),
                default=Decimal("0"),
            )
            value_max = float(value_max) if value_max > 0 else 1.0
            date_span_days = max((date_max - date_min).days, 1)

            chart_series = []
            for currency in currencies:
                points = metric_series.get(currency, [])
                if not points:
                    continue
                coords = []
                for d, v in points:
                    x = x_pad + ((d - date_min).days / date_span_days) * (chart_w - 2 * x_pad)
                    y = (chart_h - y_pad) - (float(v) / value_max) * (chart_h - 2 * y_pad)
                    coords.append((x, y))
                # SVG path: M to first, L to subsequent.
                path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
                chart_series.append(
                    {
                        "currency": currency,
                        "hue": currency_hues[currency],
                        "path_d": path_d,
                        "points": coords,
                        "latest_value": points[-1][1],
                    }
                )
            charts.append(
                {
                    "label": label,
                    "unit": unit,
                    "series": chart_series,
                    "empty": False,
                    "value_max": value_max,
                    "date_min": date_min,
                    "date_max": date_max,
                }
            )

        ctx["weeks"] = weeks
        ctx["empty"] = False
        ctx["charts"] = charts
        # Pre-pair currencies with hues so the template can iterate without
        # dict-lookup gymnastics (Django templates have no native get_item filter).
        ctx["currency_legend"] = [(c, currency_hues[c]) for c in currencies]
        ctx["chart_w"] = chart_w
        ctx["chart_h"] = chart_h
        ctx["snapshot_count"] = len(snapshots)
        ctx["today"] = date.today()
        return ctx
