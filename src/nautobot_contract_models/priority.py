"""Renewal-action priority rubric — one source of truth.

Phase 12 introduces this. Until now, the "should the operator panic"
logic lived only in :func:`RenewalCheckJob.run`, which mapped it to
``logger.warning`` vs ``logger.info``. The Phase 12 dashboard surface
needs the same rubric to drive cell colors, sort order, and badges —
duplicating the conditional in a template guarantees drift.

The rubric, in priority order:

1. **URGENT** — ``auto_renew=True`` AND inside the notice window.
   Operator MUST act or the contract auto-renews on terms they didn't
   re-negotiate.
2. **WARNING** — within 7 days of ``end_date``. Imminent renewal
   regardless of notice arrangements; action overdue.
3. **WARNING** — inside the notice window but NOT auto-renewing.
   Notice deadline matters; lapse means contract terminates rather
   than locks in, but operators usually want to act either way.
4. **INFO** — in the configured upcoming-renewals window but outside
   urgency bands above. Heads-up only.

Anything outside the upcoming-renewals window doesn't appear in the
priority surface at all (it's "not actionable yet").

The string values (``"urgent"``, ``"warning"``, ``"info"``) are stable
over time — templates and tests can match them directly. Ordering is
``URGENT > WARNING > INFO`` for sort purposes (use :data:`PRIORITY_RANK`).
"""

from datetime import date, timedelta

URGENT = "urgent"
WARNING = "warning"
INFO = "info"

# Higher rank = more attention. Use as a sort key with reverse=True.
PRIORITY_RANK = {
    URGENT: 3,
    WARNING: 2,
    INFO: 1,
}


def action_priority(contract, *, on_date=None, imminent_threshold_days=7):
    """Return ``"urgent" | "warning" | "info"`` based on contract dates.

    Returns ``None`` for contracts that don't have an ``end_date`` —
    callers can filter those out before sorting.

    ``imminent_threshold_days`` mirrors the rubric in
    :class:`RenewalCheckJob` (default 7). Operators with different
    operational tempos can pass a different threshold; the dashboard
    panel uses the default.
    """
    if on_date is None:
        on_date = date.today()
    if contract.end_date is None:
        return None

    days_remaining = (contract.end_date - on_date).days
    in_notice_window = _is_in_notice_window(contract, on_date)

    if contract.auto_renew and in_notice_window:
        return URGENT
    if 0 <= days_remaining <= imminent_threshold_days:
        return WARNING
    if in_notice_window:
        return WARNING
    return INFO


def contracts_needing_action(*, window_days=60, on_date=None):
    """Return contracts within ``window_days`` of expiry, sorted by urgency.

    Each result is a ``(contract, priority)`` tuple. Sort order is
    URGENT first, then WARNING, then INFO; within each band, soonest
    end_date first. Already-expired contracts are excluded — operators
    can't act on something that already lapsed.

    The dashboard panel and the action-required list view both consume
    this. Keeping it here means future tweaks (different sort, new
    priority bands) land in one place.
    """
    if on_date is None:
        on_date = date.today()

    # Local import keeps this module ORM-free at import time, which lets
    # priority.py be imported by tests/conftest under the lightweight mocks.
    from nautobot_contract_models.models import Contract

    cutoff = on_date + timedelta(days=int(window_days))
    qs = Contract.objects.filter(end_date__gte=on_date, end_date__lte=cutoff).select_related("provider", "status")

    rows = []
    for contract in qs:
        priority = action_priority(contract, on_date=on_date)
        if priority is None:
            continue
        rows.append((contract, priority))

    rows.sort(key=lambda row: (-PRIORITY_RANK[row[1]], row[0].end_date))
    return rows


def _is_in_notice_window(contract, on_date):
    """True when ``on_date`` is within ``notice_period_days`` of ``end_date``.

    Returns False if ``notice_period_days`` is unset / zero — there's
    no notice obligation to enforce.
    """
    notice = contract.notice_period_days or 0
    if notice <= 0:
        return False
    notice_deadline = contract.end_date - timedelta(days=int(notice))
    return notice_deadline <= on_date <= contract.end_date
