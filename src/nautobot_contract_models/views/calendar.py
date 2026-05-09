"""Renewal Calendar view — a forward-looking month-by-month renewal heat-map.

Phase 9 introduces this. It's a plain Django TemplateView rather than a
NautobotUIViewSet because it doesn't have list/detail/CRUD semantics — it's
a single read-only report page. The data comes from
:func:`cost.renewal_calendar`; the template owns presentation.

Permission: ``nautobot_contract_models.view_contract``. The page does not
restrict-by-user the way the home dashboard does — operators with the
view permission see the fleet-wide aggregate. This matches how
RenewalCheckJob behaves.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import TemplateView

from nautobot_contract_models import cost


class ContractRenewalCalendarView(PermissionRequiredMixin, TemplateView):
    """Render the 12-month forward renewal calendar.

    Window length is configurable via ``?months=N`` query param (default 12,
    capped at 36 to keep the grid readable).
    """

    template_name = "nautobot_contract_models/contract_renewal_calendar.html"
    permission_required = "nautobot_contract_models.view_contract"

    def get_context_data(self, **kwargs):
        """Build the calendar grid + per-currency rows for the template."""
        ctx = super().get_context_data(**kwargs)
        try:
            months = max(1, min(36, int(self.request.GET.get("months", 12))))
        except (TypeError, ValueError):
            months = 12

        grid = cost.renewal_calendar(months=months)

        # Pre-compute display data the template can't do without bloating itself:
        #
        # 1. The set of currencies actually present (so the template renders
        #    one row per currency, not one row per existing-currency-anywhere).
        # 2. The max value in the visible window per currency — used to
        #    normalize cell saturation. A cell containing 100% of the
        #    window's max gets the most saturated color; a cell with 25% gets
        #    a quarter the saturation.
        currencies = set()
        max_by_currency = {}
        for cell in grid:
            for currency, total in cell["totals"].items():
                currencies.add(currency)
                if total > max_by_currency.get(currency, Decimal("0")):
                    max_by_currency[currency] = total

        # Pre-pivot the data into one row per currency so the template
        # iterates without dict-lookup template gymnastics. Each row's
        # ``cells`` list is in the same chronological order as ``grid``.
        ZERO = Decimal("0")
        currencies_sorted = sorted(currencies)
        rows = []
        for currency in currencies_sorted:
            cells = []
            ceiling = max_by_currency.get(currency, ZERO)
            for cell in grid:
                total = cell["totals"].get(currency, ZERO)
                contract_names = cell.get("contracts_by_currency", {}).get(currency, [])
                saturation = int((total / ceiling) * 100) if (ceiling > 0 and total > 0) else 0
                cells.append(
                    {
                        "year": cell["year"],
                        "month": cell["month"],
                        "label": cell["label"],
                        "total": total,
                        "saturation": saturation,
                        "contract_count": cell["contract_count"],
                        "contract_names": contract_names,
                        # Newline-joined name list for the cell's title=""
                        # tooltip. Newlines render as line-breaks in browser
                        # tooltips for most engines, falling back gracefully
                        # to a space-separated list if not.
                        "tooltip": "\n".join(contract_names),
                        "is_current": cell["year"] == date.today().year and cell["month"] == date.today().month,
                    }
                )
            rows.append({"currency": currency, "cells": cells})

        # Window-selector options. The template can't `.split` a string —
        # any choice list has to come from the view.
        ctx["window_options"] = [3, 6, 12, 24, 36]
        ctx["months_grid"] = grid  # for the month-header row
        ctx["rows"] = rows
        ctx["currencies"] = currencies_sorted
        ctx["months"] = months
        ctx["today"] = date.today()
        return ctx
