"""Nautobot Jobs for the contract-models plugin.

Currently exposes :class:`RenewalCheckJob` — finds contracts expiring within
a configurable window and writes a per-contract log entry. Operators can run
it on demand from the Jobs UI, or configure a scheduled invocation via the
Nautobot scheduler so the renewal report runs nightly.

The Job's logger calls (``self.logger.info``, ``warning``, ``error``) flow
into the standard JobResult / JobLogEntry surface — operators see the output
in the Job result detail page, can search/filter past runs, and can wire
webhook hooks to JobLogEntry creation if they want notifications routed
into Slack / email / PagerDuty.
"""

from datetime import date, timedelta

from django.conf import settings
from nautobot.apps.jobs import BooleanVar, IntegerVar, Job, ObjectVar, register_jobs
from nautobot.dcim.models import Device, Location

from nautobot_contract_models import cost, priority
from nautobot_contract_models.helpers import has_active_coverage
from nautobot_contract_models.models import Contract

NAME = "Contracts"


def _default_window():
    """Resolve the default renewal window from PLUGINS_CONFIG, falling back to 60 days."""
    plugin_cfg = settings.PLUGINS_CONFIG.get("nautobot_contract_models", {})
    return int(plugin_cfg.get("renewal_window_days", 60))


class RenewalCheckJob(Job):
    """Find contracts expiring within ``window_days`` and log a summary per contract.

    Usage:
        - On-demand: Jobs → Contracts → "Check upcoming renewals" → Run
        - Scheduled: configure a recurring schedule (Jobs → Scheduled Jobs)

    The Job is read-only — it does not modify any contracts or send out
    notifications directly. Operators wire notification routing via webhook
    hooks on JobLogEntry creation.
    """

    window_days = IntegerVar(
        default=_default_window,
        description=(
            "Number of days from today to look ahead. Contracts whose end_date falls within this window are reported."
        ),
        min_value=1,
        max_value=3650,
    )
    include_expired = BooleanVar(
        default=False,
        description=(
            "Include already-expired contracts in the report. Off by default "
            "to keep the renewals view focused on what's actionable."
        ),
    )

    class Meta:
        """Job metadata — name, description, grouping, scheduling-friendliness."""

        name = "Check upcoming renewals"
        description = "Identify contracts expiring within the configured window."
        grouping = NAME
        # We take no secrets; allow operators to schedule recurring runs.
        has_sensitive_variables = False

    def run(self, window_days, include_expired):
        """Walk contracts; log each one expiring within the window.

        Returns the count of contracts reported, which surfaces as the Job
        result's "result" field in the UI for at-a-glance review.
        """
        today = date.today()
        cutoff = today + timedelta(days=window_days)

        qs = Contract.objects.select_related("provider", "tenant", "status").filter(end_date__lte=cutoff)
        if not include_expired:
            qs = qs.filter(end_date__gte=today)
        qs = qs.order_by("end_date", "name")

        if not qs.exists():
            self.logger.info(
                "No contracts found expiring within %d days (today=%s, cutoff=%s).",
                window_days,
                today,
                cutoff,
            )
            return 0

        count = 0
        for contract in qs:
            days_remaining = (contract.end_date - today).days

            # Severity rubric is centralized in priority.action_priority so the
            # dashboard, the action-required list view, and this Job all share
            # one source of truth. URGENT and WARNING both flow to logger.warning;
            # INFO maps to logger.info. Anything that returns no priority (e.g.
            # missing end_date, which the queryset already excludes) is skipped.
            tier = priority.action_priority(contract, on_date=today)
            if tier is None:
                continue
            level = self.logger.warning if tier in (priority.URGENT, priority.WARNING) else self.logger.info

            notice_window = contract.notice_period_days or 0
            days_to_notice = days_remaining - notice_window

            extra_msg = ""
            if notice_window > 0:
                extra_msg = f" Notice deadline in {days_to_notice} day(s)."
            if contract.auto_renew:
                extra_msg += " Auto-renew is ON."

            level(
                "[%s] Contract '%s' (provider=%s) expires %s — %d day(s) %s.%s",
                tier.upper(),
                contract.name,
                contract.provider.name,
                contract.end_date,
                abs(days_remaining),
                "remaining" if days_remaining >= 0 else "ago",
                extra_msg,
                extra={"object": contract},
            )
            count += 1

        self.logger.info(
            "Renewal check complete: %d contract(s) within %d-day window.",
            count,
            window_days,
        )
        return count


class CoverageGapJob(Job):
    """Find Devices with no active contract coverage and log each one.

    Walks the configured Devices (optionally filtered by Location) and uses
    the transitive coverage helper — so a Device is "covered" if it OR its
    Location OR its Tenant (etc.) has any active ContractAssignment today.

    Read-only. Logs one entry per uncovered Device at WARNING level so a
    JobLogEntry webhook can route the list into Slack / email / a ticket.
    """

    location = ObjectVar(
        model=Location,
        required=False,
        description=(
            "If set, restrict the report to Devices at this Location "
            "(descendants are NOT walked — set this to a leaf location for a focused report)."
        ),
    )

    class Meta:
        """Job metadata."""

        name = "Find devices without contract coverage"
        description = (
            "Walk Devices and report each one with no active contract coverage (direct or via Tenant/Location)."
        )
        grouping = NAME
        has_sensitive_variables = False

    def run(self, location=None):
        """Walk Devices, log each one without active coverage. Returns the count."""
        qs = Device.objects.select_related("location", "tenant")
        if location is not None:
            qs = qs.filter(location=location)
        qs = qs.order_by("location__name", "name")

        uncovered = 0
        scanned = 0
        for device in qs:
            scanned += 1
            if has_active_coverage(device):
                continue
            uncovered += 1
            self.logger.warning(
                "Device '%s' (location=%s, tenant=%s) has no active contract coverage.",
                device.name,
                device.location.name if device.location else "—",
                device.tenant.name if device.tenant else "—",
                extra={"object": device},
            )

        self.logger.info(
            "Coverage gap scan complete: %d of %d device(s) lack coverage.",
            uncovered,
            scanned,
        )
        return uncovered


class CostReportJob(Job):
    """Log a snapshot of fleet-wide contract costs to JobLogEntry.

    Read-only. Operators schedule this weekly to get a cost trend in the
    Job result history without running a separate time-series store —
    each scheduled run becomes a row of JobLogEntry that can be searched,
    exported, or piped to a notification webhook.

    Fields logged:
        - Monthly burn rate per currency
        - 90-day renewal cost per currency
        - Top vendor by current monthly spend
        - Direct coverage-gap count (Devices with no direct ContractAssignment)
    """

    forecast_window_days = IntegerVar(
        default=90,
        description="Forecast window for the renewal-cost line. Defaults to 90 days.",
        min_value=1,
        max_value=3650,
    )

    class Meta:
        """Job metadata."""

        name = "Monthly cost report"
        description = "Log monthly burn rate, renewal forecast, top vendor, and coverage gap count."
        grouping = NAME
        has_sensitive_variables = False

    def run(self, forecast_window_days):
        """Compute the cost summary and write per-line INFO log entries."""
        burn = cost.burn_rate_by_currency()
        renewal = cost.renewal_cost_in_window(forecast_window_days)
        top_vendors = cost.spend_by_vendor(limit=1)
        gap_count = cost.coverage_gap_count()

        if not burn:
            self.logger.info("No active contracts — burn rate is zero across all currencies.")
        else:
            for currency, total in burn.items():
                self.logger.info("Monthly burn (%s): %s", currency, total)

        if not renewal:
            self.logger.info("No contracts renewing in the next %d day(s).", forecast_window_days)
        else:
            for currency, total in renewal.items():
                self.logger.info(
                    "%d-day renewal cost (%s): %s",
                    forecast_window_days,
                    currency,
                    total,
                )

        if top_vendors:
            provider, monthly, currency = top_vendors[0]
            self.logger.info("Top vendor by monthly spend: %s (%s %s/mo)", provider.name, monthly, currency)

        # Coverage-gap count uses the cheap direct-only query — operators
        # who want the transitive answer should run CoverageGapJob.
        self.logger.info("Devices without a direct contract assignment: %d", gap_count)

        return {
            "burn": {c: str(v) for c, v in burn.items()},
            "renewal": {c: str(v) for c, v in renewal.items()},
            "coverage_gaps": gap_count,
        }


register_jobs(RenewalCheckJob, CoverageGapJob, CostReportJob)
