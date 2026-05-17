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

import re
from datetime import date, timedelta
from decimal import Decimal

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from nautobot.apps.jobs import BooleanVar, ChoiceVar, IntegerVar, Job, ObjectVar, register_jobs
from nautobot.dcim.models import Device, Location

from nautobot_contract_models import cost, priority
from nautobot_contract_models.choices import (
    BillingPeriodChoices,
    ContractTypeChoices,
    CoverageHoursChoices,
    ResponseTimeChoices,
)
from nautobot_contract_models.helpers import has_active_coverage
from nautobot_contract_models.models import Contract, ContractAssignment, ServiceProvider

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


class CostHistoryJob(Job):
    """Persist a CostSnapshot per currency for today's date.

    Operators schedule this weekly. Each run creates (or refreshes)
    snapshot rows that drive the cost-history visualization. Re-running
    the same day is idempotent — the unique (snapshot_date, currency)
    constraint plus update_or_create means duplicates can't accumulate.

    Distinct from CostReportJob: CostReportJob writes to JobLogEntry
    (ephemeral, search-but-not-queryable). CostHistoryJob writes to
    a real model so we can render time-series UI.
    """

    class Meta:
        """Job metadata."""

        name = "Capture cost history snapshot"
        description = "Persist a per-currency CostSnapshot row for today's burn / renewal / contract count."
        grouping = NAME
        has_sensitive_variables = False

    def run(self):
        """Take a snapshot and log one INFO line per currency captured."""
        snapshots = cost.take_snapshot()

        if not snapshots:
            self.logger.info("No active contracts — no snapshot rows created.")
            return 0

        for snap in snapshots:
            self.logger.info(
                "Snapshot %s %s: monthly_burn=%s · renewal_90d=%s · contracts=%d",
                snap.snapshot_date,
                snap.currency,
                snap.monthly_burn,
                snap.renewal_90d,
                snap.active_contract_count,
                extra={"object": snap},
            )
        self.logger.info("Captured %d snapshot row(s) for %s.", len(snapshots), snapshots[0].snapshot_date)
        return len(snapshots)


class CostAnomalyJob(Job):
    """Diff this week's cost snapshots against ``lookback_weeks`` ago, log anomalies.

    Read-only. Operators schedule weekly to get an alert when burn rate
    or renewal forecast changes by more than ``threshold_pct`` from the
    historical baseline. Hooks into existing JobLogEntry webhook plumbing,
    so anomalies can route into Slack / email / a ticket.

    Requires that ``CostHistoryJob`` has been running long enough to
    have a snapshot at-or-before (today - lookback_weeks). Without
    historical data the helper reports nothing and the Job logs an INFO
    line saying so.
    """

    threshold_pct = IntegerVar(
        default=20,
        description="Percent change threshold (1-200). Changes below this are noise; above are anomalies.",
        min_value=1,
        max_value=200,
    )
    lookback_weeks = IntegerVar(
        default=4,
        description="How many weeks back to compare today's snapshot against.",
        min_value=1,
        max_value=52,
    )

    class Meta:
        """Job metadata."""

        name = "Detect cost anomalies"
        description = "Flag week-over-week (or N-week) jumps in monthly burn / renewal forecast."
        grouping = NAME
        has_sensitive_variables = False

    def run(self, threshold_pct, lookback_weeks):
        """Compute anomalies and emit one WARNING per finding."""
        from decimal import Decimal as D

        threshold = D(threshold_pct) / D(100)
        anomalies = cost.detect_anomalies(threshold=threshold, lookback_weeks=lookback_weeks)

        if not anomalies:
            self.logger.info(
                "No anomalies — all currency/metric pairs within %d%% of %d-week baseline.",
                threshold_pct,
                lookback_weeks,
            )
            return 0

        for a in anomalies:
            arrow = "↑" if a["direction"] == "up" else "↓"
            if a["pct_change"] is None:
                pct_str = "NEW"
            else:
                pct_str = f"{a['pct_change'] * 100:+.1f}%"
            self.logger.warning(
                "Anomaly: %s %s %s %s → %s (%s vs %d weeks ago).",
                a["currency"],
                a["metric"],
                arrow,
                a["prev_value"],
                a["current_value"],
                pct_str,
                lookback_weeks,
            )
        self.logger.info("Detected %d anomal%s.", len(anomalies), "y" if len(anomalies) == 1 else "ies")
        return len(anomalies)


# --- Phase 19: DLM ContractLCM → Contract migration --------------------------
#
# DLM stores `support_level` and `contract_type` as free-text on every
# ContractLCM, while we model them as enums (Phase 7). We do a best-effort
# regex mapping on migration and warn-and-leave-blank when no pattern matches.
# Operators can fix unmapped values in the UI afterward — partial mapping is
# more useful than dropping the migration when one row's free-text is weird.

_SUPPORT_LEVEL_PATTERNS = (
    # Each tuple: (regex, coverage_hours_choice_or_blank, response_time_choice_or_blank)
    (re.compile(r"\b8x5.*nbd\b|\b8-5.*nbd\b", re.I), CoverageHoursChoices.HOURS_8X5_NBD, ResponseTimeChoices.NBD),
    (re.compile(r"\b24x7\b|\b24/7\b|\b24-7\b", re.I), CoverageHoursChoices.HOURS_24X7, ""),
    (re.compile(r"\b24x5\b|\b24-5\b", re.I), CoverageHoursChoices.HOURS_24X5, ""),
    (re.compile(r"business hours|\b9-5\b|9 to 5", re.I), CoverageHoursChoices.HOURS_BUSINESS, ""),
    (re.compile(r"best.?effort", re.I), CoverageHoursChoices.HOURS_BEST_EFFORT, ResponseTimeChoices.BEST_EFFORT),
    (re.compile(r"\bnbd\b|next business day", re.I), "", ResponseTimeChoices.NBD),
    # [\s-]* tolerates both "4 hour" and "4-hour" (real-world copy uses both).
    (re.compile(r"\b1[\s-]*hour\b|\b1h\b", re.I), "", ResponseTimeChoices.HOURS_1),
    (re.compile(r"\b2[\s-]*hours?\b|\b2h\b", re.I), "", ResponseTimeChoices.HOURS_2),
    (re.compile(r"\b4[\s-]*hours?\b|\b4h\b", re.I), "", ResponseTimeChoices.HOURS_4),
    (re.compile(r"\b8[\s-]*hours?\b|\b8h\b", re.I), "", ResponseTimeChoices.HOURS_8),
)


def _map_support_level(value):
    """Best-effort regex mapping. Returns ``(coverage_hours, response_time)`` — either may be ``""``.

    Multiple patterns may match the same string ("8x5xNBD" hits both 8x5 and NBD); we
    take the first non-blank value seen for each axis. Empty input returns ``("", "")``.
    """
    if not value:
        return ("", "")
    coverage, response = "", ""
    for pattern, cov, resp in _SUPPORT_LEVEL_PATTERNS:
        if pattern.search(value):
            if cov and not coverage:
                coverage = cov
            if resp and not response:
                response = resp
    return (coverage, response)


_CONTRACT_TYPE_PATTERNS = (
    (re.compile(r"saas", re.I), ContractTypeChoices.SAAS),
    (re.compile(r"hardware|\bhw\b|maintenance", re.I), ContractTypeChoices.HARDWARE),
    (re.compile(r"software|subscription|license", re.I), ContractTypeChoices.SOFTWARE),
    (re.compile(r"managed", re.I), ContractTypeChoices.MANAGED),
    (re.compile(r"professional|consulting", re.I), ContractTypeChoices.SERVICES),
    (re.compile(r"warranty", re.I), ContractTypeChoices.WARRANTY),
    (re.compile(r"support", re.I), ContractTypeChoices.SUPPORT),
    # NB: we deliberately don't auto-map to OTHER — operators may want to pick
    # something more specific manually after migration.
)


def _map_contract_type(value):
    """Best-effort regex mapping. Returns a ContractTypeChoices value or ``""``."""
    if not value:
        return ""
    for pattern, choice in _CONTRACT_TYPE_PATTERNS:
        if pattern.search(value):
            return choice
    return ""


def _resolve_status(lcm_status):
    """Map a ContractLCM.status to a Status valid for our Contract model.

    StatusFields bind to extras.Status via ContentType, so a Status set up for
    DLM's ContractLCM may or may not be on our Contract's status ContentType.
    Strategy: (1) accept the same Status row if it's bound to Contract;
    (2) try a same-name lookup on the Contract-bound queryset; (3) fall back
    to ``Active`` for Contract; (4) return None and let the caller skip.
    """
    from nautobot.extras.models import Status

    valid = Status.objects.get_for_model(Contract)
    if lcm_status and valid.filter(pk=lcm_status.pk).exists():
        return lcm_status
    if lcm_status:
        match = valid.filter(name=lcm_status.name).first()
        if match:
            return match
    return valid.filter(name="Active").first()


class MigrateContractLCMToContract(Job):
    """Migrate every ContractLCM row from ``nautobot-app-device-lifecycle-mgmt`` into our Contract model.

    Mirrors DLM's own :class:`DLMToNautobotCoreModelMigration` Job idiom: each
    source ContractLCM gets stamped with a custom-field marker
    ``migrated_to_contract_models=True`` after migration, so re-runs are
    idempotent — already-stamped rows are excluded from the queryset.

    One-way. Source ContractLCM rows are stamped but NOT deleted; operators
    delete from DLM's UI when they're confident the migration is correct.

    Maps the ``ContractLCM.devices`` M2M into our polymorphic
    :class:`ContractAssignment` rows (one per Device, content_type=dcim.Device).
    """

    dry_run = BooleanVar(
        default=True,
        description=(
            "Log planned actions without writing. Run with dry_run=True first to verify "
            "the field mapping and provider matching, then again with dry_run=False to commit."
        ),
    )
    default_billing_period = ChoiceVar(
        choices=BillingPeriodChoices.CHOICES,
        default=BillingPeriodChoices.MONTHLY,
        description=(
            "DLM's ContractLCM.cost is a flat decimal with no cadence — we interpret it "
            "as recurring at this cadence. If your DLM contracts stored annual prices, "
            "set this to 'Annual'."
        ),
    )
    provider_match_strategy = ChoiceVar(
        choices=(
            ("by_name", "Match by name; create ServiceProvider if missing"),
            ("by_name_strict", "Match by name; skip the contract if no ServiceProvider matches"),
        ),
        default="by_name",
        description="How to map DLM's ProviderLCM to our ServiceProvider.",
    )

    class Meta:
        """Job metadata."""

        name = "Migrate ContractLCM → Contract"
        description = (
            "Copy every ContractLCM row from nautobot-app-device-lifecycle-mgmt into our "
            "Contract model. Idempotent — re-running skips already-migrated rows. "
            "One-way: source ContractLCM rows are stamped with a custom field but NOT deleted."
        )
        grouping = NAME
        has_sensitive_variables = False

    def run(self, dry_run, default_billing_period, provider_match_strategy):
        """Walk unmarked ContractLCM rows, copy to Contract + ContractAssignment, stamp the source.

        Returns a dict summarizing counts; surfaces as the JobResult "result" field.
        """
        if not django_apps.is_installed("nautobot_device_lifecycle_mgmt"):
            self.logger.error("nautobot-app-device-lifecycle-mgmt is not installed; nothing to migrate.")
            return {"migrated": 0, "skipped": 0, "warnings": 0, "assignments": 0, "dry_run": dry_run}

        from nautobot.extras.choices import CustomFieldTypeChoices
        from nautobot.extras.models import CustomField
        from nautobot_device_lifecycle_mgmt.models import ContractLCM

        # 1. Ensure the marker custom field exists and is bound to ContractLCM.
        # Mirrors DLM's own `migrated_to_core_model_flag` pattern in their
        # DLMToNautobotCoreModelMigration job.
        contractlcm_ct = ContentType.objects.get_for_model(ContractLCM)
        if not dry_run:
            cf, created = CustomField.objects.get_or_create(
                key="migrated_to_contract_models",
                defaults={
                    "label": "Migrated to Contract Models",
                    "type": CustomFieldTypeChoices.TYPE_BOOLEAN,
                    "default": False,
                },
            )
            cf.content_types.add(contractlcm_ct)
            if created:
                self.logger.info("Created custom field 'migrated_to_contract_models' on ContractLCM.")

        # 2. Query unmarked rows. We use `__contains={...: True}` rather than
        # `__migrated_to_contract_models=True` because Django's JSONField
        # path-extract returns NULL for absent keys, and `.exclude(=True)`
        # then drops those rows too (NULL comparisons aren't True). The
        # `__contains` lookup is a JSON subset-match — absent keys simply
        # don't match, so they survive the exclude.
        marker = {"migrated_to_contract_models": True}
        unmarked = (
            ContractLCM.objects.exclude(_custom_field_data__contains=marker)
            .select_related("provider")
            .prefetch_related("devices")
        )

        total = unmarked.count()
        if total == 0:
            self.logger.info("All ContractLCM rows are already migrated. Nothing to do.")
            return {"migrated": 0, "skipped": 0, "warnings": 0, "assignments": 0, "dry_run": dry_run}

        self.logger.info("Found %d ContractLCM row(s) to consider (dry_run=%s).", total, dry_run)

        migrated = 0
        assignments_created = 0
        skipped = 0
        warnings = 0
        device_ct = ContentType.objects.get_for_model(Device)

        for lcm in unmarked:
            outcome = self._migrate_one(
                lcm=lcm,
                dry_run=dry_run,
                default_billing_period=default_billing_period,
                provider_match_strategy=provider_match_strategy,
                device_ct=device_ct,
            )
            if outcome.get("skipped"):
                skipped += 1
            else:
                migrated += 1
            assignments_created += outcome.get("assignments", 0)
            warnings += outcome.get("warnings", 0)

        summary_prefix = "DRY-RUN: " if dry_run else ""
        self.logger.info(
            "%sMigration complete: %d migrated, %d skipped, %d assignment row(s) created, %d warning(s).",
            summary_prefix,
            migrated,
            skipped,
            assignments_created,
            warnings,
        )
        return {
            "migrated": migrated,
            "skipped": skipped,
            "assignments": assignments_created,
            "warnings": warnings,
            "dry_run": dry_run,
        }

    def _migrate_one(self, *, lcm, dry_run, default_billing_period, provider_match_strategy, device_ct):
        """Migrate a single ContractLCM row. Returns ``{skipped, assignments, warnings}``."""
        warnings = 0

        # --- Provider mapping ---
        provider_name = lcm.provider.name if lcm.provider else None
        if not provider_name:
            self.logger.warning(
                "[skip] ContractLCM '%s' has no provider; skipping.",
                lcm.name,
                extra={"object": lcm},
            )
            return {"skipped": True, "assignments": 0, "warnings": 1}

        # --- Date validation (ours requires start_date AND end_date) ---
        if lcm.start is None or lcm.end is None:
            self.logger.warning(
                "[skip] ContractLCM '%s' missing start/end dates; skipping (ours requires both).",
                lcm.name,
                extra={"object": lcm},
            )
            return {"skipped": True, "assignments": 0, "warnings": 1}

        # --- Status mapping ---
        status = _resolve_status(lcm.status)
        if status is None:
            self.logger.warning(
                "[skip] ContractLCM '%s' has no usable Status (and no 'Active' Status exists for Contract).",
                lcm.name,
                extra={"object": lcm},
            )
            return {"skipped": True, "assignments": 0, "warnings": 1}

        # --- Free-text → enum mappings (best-effort, warn-and-leave-blank) ---
        support_level = (lcm.support_level or "").strip()
        coverage_hours, response_time = _map_support_level(support_level)
        if support_level and not (coverage_hours or response_time):
            self.logger.warning(
                "[unmapped] ContractLCM '%s' support_level=%r — leaving coverage_hours/response_time blank.",
                lcm.name,
                support_level,
                extra={"object": lcm},
            )
            warnings += 1

        contract_type_raw = (lcm.contract_type or "").strip()
        contract_type = _map_contract_type(contract_type_raw)
        if contract_type_raw and not contract_type:
            self.logger.warning(
                "[unmapped] ContractLCM '%s' contract_type=%r — leaving blank.",
                lcm.name,
                contract_type_raw,
                extra={"object": lcm},
            )
            warnings += 1

        currency = (lcm.currency or "").strip() or "USD"
        cost_value = lcm.cost if lcm.cost is not None else Decimal("0.00")
        billing_period = default_billing_period if cost_value > 0 else BillingPeriodChoices.MONTHLY
        device_count = lcm.devices.count()

        if dry_run:
            self.logger.info(
                "[dry-run] Would migrate ContractLCM '%s' → Contract "
                "(provider=%s, cost=%s %s/%s, devices=%d, status=%s).",
                lcm.name,
                provider_name,
                cost_value,
                currency,
                billing_period,
                device_count,
                status.name,
                extra={"object": lcm},
            )
            return {"skipped": False, "assignments": device_count, "warnings": warnings}

        # --- Commit phase: provider, contract, assignments, source stamp — all in one txn ---
        with transaction.atomic():
            provider = ServiceProvider.objects.filter(name=provider_name).first()
            if provider is None:
                if provider_match_strategy == "by_name_strict":
                    self.logger.warning(
                        "[skip] No ServiceProvider matches %r for ContractLCM '%s' (strict mode).",
                        provider_name,
                        lcm.name,
                        extra={"object": lcm},
                    )
                    return {"skipped": True, "assignments": 0, "warnings": warnings + 1}
                provider = ServiceProvider.objects.create(
                    name=provider_name,
                    description="Migrated from nautobot-app-device-lifecycle-mgmt",
                )
                self.logger.info("[provider+] Created ServiceProvider '%s'.", provider_name)

            new_contract = Contract.objects.create(
                name=lcm.name,
                contract_number=(lcm.number or "")[:100],
                provider=provider,
                status=status,
                start_date=lcm.start,
                end_date=lcm.end,
                recurring_cost=cost_value,
                billing_period=billing_period,
                currency=currency,
                contract_type=contract_type,
                coverage_hours=coverage_hours,
                response_time=response_time,
                description=f"[Migrated from DLM ContractLCM {lcm.pk}]"[:200],
                comments=lcm.comments or "",
            )

            assignments = 0
            for device in lcm.devices.all():
                ContractAssignment.objects.create(
                    contract=new_contract,
                    content_type=device_ct,
                    object_id=device.pk,
                    is_primary=False,
                )
                assignments += 1

            # Stamp the source as migrated.
            lcm._custom_field_data = dict(lcm._custom_field_data or {})
            lcm._custom_field_data["migrated_to_contract_models"] = True
            lcm.save()

        self.logger.info(
            "[ok] Migrated ContractLCM '%s' → Contract (devices=%d).",
            lcm.name,
            assignments,
            extra={"object": lcm},
        )
        return {"skipped": False, "assignments": assignments, "warnings": warnings}


# --- end Phase 19 ------------------------------------------------------------


# --- Phase 20: CoverageSnapshotJob -------------------------------------------
#
# Persist a per-device snapshot of coverage state. Feeds the Coverage Drift
# view which diffs two snapshots N days apart to identify devices that
# *lost* coverage (or gained it). Mirrors CostHistoryJob's pattern but
# stores per-device rows, not per-currency aggregates.


class CoverageSnapshotJob(Job):
    """Snapshot every Device's coverage state into a CoverageSnapshot row.

    Operators schedule this weekly. Each run records one row per device
    capturing whether the device had active contract coverage (direct or
    transitive) on today's date. Idempotent via UniqueConstraint on
    (snapshot_date, device) + update_or_create — re-running the same day
    refreshes the row rather than failing.

    Coverage Drift view (``/plugins/contracts/reports/coverage-drift/``)
    diffs two snapshot dates N days apart to surface devices that
    *gained* or *lost* coverage.
    """

    class Meta:
        """Job metadata."""

        name = "Capture coverage snapshot"
        description = "Persist a per-device CoverageSnapshot row for today's coverage state. Feeds the drift report."
        grouping = NAME
        has_sensitive_variables = False

    def run(self):
        """Walk Device.objects.all() and write one CoverageSnapshot per device."""
        from nautobot_contract_models.helpers import has_active_coverage
        from nautobot_contract_models.models import CoverageSnapshot

        today = date.today()
        # select_related the ancestors has_active_coverage walks so we
        # don't N+1 on tenant/location/rack lookups per device.
        devices = Device.objects.select_related("location", "tenant", "rack").iterator()

        covered_count = 0
        uncovered_count = 0
        for device in devices:
            covered = has_active_coverage(device, on_date=today)
            CoverageSnapshot.objects.update_or_create(
                snapshot_date=today,
                device=device,
                defaults={"was_covered": covered},
            )
            if covered:
                covered_count += 1
            else:
                uncovered_count += 1

        total = covered_count + uncovered_count
        self.logger.info(
            "Coverage snapshot for %s: %d devices total — %d covered, %d uncovered.",
            today,
            total,
            covered_count,
            uncovered_count,
        )
        return {
            "snapshot_date": today.isoformat(),
            "devices_total": total,
            "devices_covered": covered_count,
            "devices_uncovered": uncovered_count,
        }


# --- end Phase 20 ------------------------------------------------------------


register_jobs(
    RenewalCheckJob,
    CoverageGapJob,
    CostReportJob,
    CostHistoryJob,
    CostAnomalyJob,
    MigrateContractLCMToContract,
    CoverageSnapshotJob,
)
