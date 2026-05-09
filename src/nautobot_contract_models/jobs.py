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
from nautobot.apps.jobs import BooleanVar, IntegerVar, Job, register_jobs

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
            level = self.logger.warning if days_remaining <= 7 else self.logger.info
            level(
                "Contract '%s' (provider=%s) expires %s — %d day(s) %s.",
                contract.name,
                contract.provider.name,
                contract.end_date,
                abs(days_remaining),
                "remaining" if days_remaining >= 0 else "ago",
                extra={"object": contract},
            )
            count += 1

        self.logger.info(
            "Renewal check complete: %d contract(s) within %d-day window.",
            count,
            window_days,
        )
        return count


register_jobs(RenewalCheckJob)
