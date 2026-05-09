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

            # If a notice period is set, the actionable date is end_date - notice_period_days.
            # Once we're inside the notice window, urgency jumps regardless of days_remaining.
            notice_window = contract.notice_period_days or 0
            days_to_notice = days_remaining - notice_window
            in_notice_window = notice_window > 0 and days_to_notice <= 0

            # Severity rubric:
            #   - in notice window for an auto-renewing contract: WARNING (action needed to avoid lock-in)
            #   - <= 7 days remaining: WARNING
            #   - everything else: INFO
            if (in_notice_window and contract.auto_renew) or days_remaining <= 7:
                level = self.logger.warning
            else:
                level = self.logger.info

            extra_msg = ""
            if notice_window > 0:
                extra_msg = f" Notice deadline in {days_to_notice} day(s)."
            if contract.auto_renew:
                extra_msg += " Auto-renew is ON."

            level(
                "Contract '%s' (provider=%s) expires %s — %d day(s) %s.%s",
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


register_jobs(RenewalCheckJob, CoverageGapJob)
