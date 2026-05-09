"""Homepage panel for the contract-models plugin.

Renders an "Upcoming Renewals" panel on Nautobot's home dashboard. The panel
shows the same data the :class:`RenewalCheckJob` reports — contracts with
``end_date`` within the configured window — but at-a-glance instead of as a
Job log. Each row links straight to the contract detail page so operators can
click through to the signed-PDF attachment, the invoice history, etc.

Window comes from ``PLUGINS_CONFIG['nautobot_contract_models']
['renewal_window_days']`` (default 60). The :func:`get_upcoming_renewals`
callable is evaluated at template-render time, so the panel reflects current
state — adding a new contract or extending an end_date updates the home
dashboard on the next page load.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from nautobot.apps.ui import HomePagePanel
from nautobot.dcim.models import Device

from nautobot_contract_models import cost
from nautobot_contract_models.helpers import has_active_coverage
from nautobot_contract_models.models import Contract


def _renewal_window_days():
    return int(settings.PLUGINS_CONFIG.get("nautobot_contract_models", {}).get("renewal_window_days", 60))


def get_upcoming_renewals(request):
    """Return contracts expiring within the configured window, ordered by soonest.

    The ``request`` argument is what Nautobot's homepage rendering machinery
    passes — we use it to filter the queryset by the current user's view
    permissions so the panel never shows rows the user can't see in detail.
    """
    today = date.today()
    cutoff = today + timedelta(days=_renewal_window_days())
    return (
        Contract.objects.restrict(request.user, "view")
        .select_related("provider", "tenant", "status")
        .filter(end_date__gte=today, end_date__lte=cutoff)
        .order_by("end_date", "name")[:10]
    )


def get_uncovered_devices(request):
    """Return up to 10 Devices with no active contract coverage.

    Uses the transitive helper — a Device with a Tenant- or Location-level
    contract assignment counts as covered even if it has no direct
    assignment of its own. Restricted to Devices the user can view.
    """
    qs = Device.objects.restrict(request.user, "view").select_related("location", "tenant").order_by("name")
    # Naive Python-side filter — fine for the dashboard's first-10 cap.
    # A more scalable version would push the existence check into SQL via a
    # subquery; keep this simple until operators report dashboard slowness.
    uncovered = []
    for device in qs.iterator():
        if not has_active_coverage(device):
            uncovered.append(device)
            if len(uncovered) >= 10:
                break
    return uncovered


def get_cost_summary(request):
    """Build the Cost Summary panel context.

    Returns burn-rate-by-currency, an annualized version (burn × 12 — done
    here in Python because Django's template ``widthratio`` is integer-only
    and would lose decimal precision), and the top-vendor list.
    """
    burn = cost.burn_rate_by_currency()
    annualized = {currency: total * Decimal("12") for currency, total in burn.items()}
    top_vendors = cost.spend_by_vendor(limit=5)
    return {
        "burn_by_currency": burn,
        "annualized_by_currency": annualized,
        "top_vendors": top_vendors,
    }


def get_renewal_forecast(request):
    """Build the Renewal Forecast panel context.

    Three windows: 30, 90, 365 days. Each entry is a (label, dict[currency, Decimal])
    tuple so the template can render rows without computing anything.
    """
    return [
        ("Next 30 days", cost.renewal_cost_in_window(30)),
        ("Next 90 days", cost.renewal_cost_in_window(90)),
        ("Next 365 days", cost.renewal_cost_in_window(365)),
    ]


layout = (
    HomePagePanel(
        name="Contracts",
        weight=1500,
        permissions=["nautobot_contract_models.view_contract"],
        custom_data={"upcoming_renewals": get_upcoming_renewals},
        custom_template="upcoming_renewals_panel.html",
    ),
    HomePagePanel(
        name="Coverage Gaps",
        weight=1510,
        permissions=["dcim.view_device"],
        custom_data={"uncovered_devices": get_uncovered_devices},
        custom_template="uncovered_devices_panel.html",
    ),
    HomePagePanel(
        name="Cost Summary",
        weight=1520,
        permissions=["nautobot_contract_models.view_contract"],
        # Single context variable holding all three sub-values. The template
        # reads ``cost_summary.burn_by_currency`` etc. — one queryset pass
        # per render rather than three.
        custom_data={"cost_summary": get_cost_summary},
        custom_template="cost_summary_panel.html",
    ),
    HomePagePanel(
        name="Renewal Forecast",
        weight=1530,
        permissions=["nautobot_contract_models.view_contract"],
        custom_data={"renewal_forecast": get_renewal_forecast},
        custom_template="renewal_forecast_panel.html",
    ),
)
