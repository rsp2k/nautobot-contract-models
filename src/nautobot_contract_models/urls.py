"""URL routing for the contract-models plugin.

The :class:`NautobotUIViewSetRouter` introspects each viewset and emits the
canonical URL patterns for list / detail / create / edit / delete / bulk-edit
/ bulk-delete / import / export, all named consistently as
``plugins:nautobot_contract_models:<model>_<action>`` (e.g.
``plugins:nautobot_contract_models:contract_list``). Tables and forms in this
plugin reference those name-strings.
"""

from django.urls import path
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_contract_models.views import (
    ContractActionRequiredView,
    ContractAssignmentUIViewSet,
    ContractAttachmentUIViewSet,
    ContractCostHistoryView,
    ContractCoverageDriftView,
    ContractICalExportView,
    ContractRenewalCalendarView,
    ContractUIViewSet,
    ICalTokenManageView,
    InvoiceAttachmentUIViewSet,
    InvoiceUIViewSet,
    ServiceProviderUIViewSet,
)

router = NautobotUIViewSetRouter()
router.register("service-providers", ServiceProviderUIViewSet)
router.register("contracts", ContractUIViewSet)
router.register("contract-attachments", ContractAttachmentUIViewSet)
router.register("invoices", InvoiceUIViewSet)
router.register("invoice-attachments", InvoiceAttachmentUIViewSet)
router.register("contract-assignments", ContractAssignmentUIViewSet)

app_name = "nautobot_contract_models"
# Reports are non-CRUD; they live OUTSIDE the router-managed prefixes.
# Why ``reports/`` rather than ``contracts/``: the router owns ``contracts/*``
# and treats any unmatched suffix as a candidate UUID — putting
# ``contracts/calendar/`` here would collide with the auto-generated
# ``contracts/<uuid>/`` detail route, giving a 500 ("calendar is not a
# valid UUID"). The ``reports/`` prefix has no router rules and matches
# the navigation menu's "Reports" group label.
urlpatterns = [
    path(
        "reports/renewal-calendar/",
        ContractRenewalCalendarView.as_view(),
        name="contract_renewal_calendar",
    ),
    path(
        "reports/action-required/",
        ContractActionRequiredView.as_view(),
        name="contract_action_required",
    ),
    path(
        "reports/cost-history/",
        ContractCostHistoryView.as_view(),
        name="contract_cost_history",
    ),
    # --- Phase 20 routes ----------------------------------------------------
    path(
        "reports/coverage-drift/",
        ContractCoverageDriftView.as_view(),
        name="contract_coverage_drift",
    ),
    # iCal export uses ``.ics`` rather than a directory path so calendar apps
    # that infer MIME from extension recognize it without the operator having
    # to muck with content-type sniffing.
    path(
        "contracts.ics",
        ContractICalExportView.as_view(),
        name="contract_ical_export",
    ),
    path(
        "ical-token/",
        ICalTokenManageView.as_view(),
        name="ical_token_manage",
    ),
] + router.urls
