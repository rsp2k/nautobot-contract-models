"""Cost-analytics helpers — burn rate, renewal forecast, vendor spend.

Phase 8 introduces ``Contract.billing_period`` so we can normalize across
contracts that bill at different cadences. These helpers do the per-contract
math (``monthly_cost``, ``annual_cost``, ``total_contract_value``) and the
fleet-wide aggregations (``burn_rate_by_currency``, ``renewal_cost_in_window``,
``spend_by_vendor``).

Aggregations always group by ``Contract.currency``. We do NOT do FX
conversion in v1 — summing $5,000 + €4,000 into a single number is wrong
in three different ways (which exchange rate? as of when? for which
purpose?), so the helpers return ``dict[currency_code, Decimal]`` and let
the dashboard render each currency on its own row.

The per-contract helpers are pure functions of one Contract instance — no
queries — so they're cheap to call inside a template loop. The
fleet-wide helpers each do exactly one queryset over Contract.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count

from nautobot_contract_models.choices import BillingPeriodChoices
from nautobot_contract_models.models import Contract

ZERO = Decimal("0.00")


def monthly_cost(contract):
    """Return ``contract.recurring_cost`` normalized to a per-month figure.

    A ``one_time`` contract returns 0 — its cost belongs in
    :func:`total_contract_value`, not the burn rate. A blank/unknown
    period falls back to monthly (the migration default).
    """
    cost = contract.recurring_cost or ZERO
    period = contract.billing_period

    if period == BillingPeriodChoices.MONTHLY:
        return cost
    if period == BillingPeriodChoices.QUARTERLY:
        return cost / Decimal("3")
    if period == BillingPeriodChoices.SEMIANNUAL:
        return cost / Decimal("6")
    if period == BillingPeriodChoices.ANNUAL:
        return cost / Decimal("12")
    if period == BillingPeriodChoices.ONE_TIME:
        return ZERO
    return cost  # blank or unknown — assume monthly


def annual_cost(contract):
    """Return ``contract.recurring_cost`` annualized.

    For ``one_time`` contracts this is also 0, mirroring :func:`monthly_cost`.
    """
    return monthly_cost(contract) * Decimal("12")


def total_contract_value(contract):
    """Total cost over the contract's full term, including one-time fees.

    Uses ``term_months`` if set; otherwise assumes a 12-month term for the
    purpose of this estimate. The one_time_cost is always added.
    """
    term = contract.term_months or 12
    if contract.billing_period == BillingPeriodChoices.ONE_TIME:
        # All the value is in the one-time + recurring fields together —
        # the recurring_cost on a one-time contract is conventionally 0
        # but we don't enforce that, so include both.
        return (contract.recurring_cost or ZERO) + (contract.one_time_cost or ZERO)
    return monthly_cost(contract) * Decimal(term) + (contract.one_time_cost or ZERO)


def _active_contracts_qs(on_date):
    """Contracts active on ``on_date`` (start <= on_date <= end)."""
    return Contract.objects.filter(start_date__lte=on_date, end_date__gte=on_date)


def burn_rate_by_currency(*, on_date=None):
    """Sum :func:`monthly_cost` across active contracts, grouped by currency.

    Returns a ``dict[currency_code, Decimal]``. Currencies with no active
    contracts simply don't appear in the dict. Dashboard rendering should
    iterate over the dict and show one row per currency.
    """
    if on_date is None:
        on_date = date.today()

    totals = defaultdict(lambda: ZERO)
    for contract in _active_contracts_qs(on_date).only("recurring_cost", "billing_period", "currency"):
        totals[contract.currency] += monthly_cost(contract)
    return dict(totals)


def renewal_cost_in_window(window_days, *, on_date=None):
    """Total contract value for contracts whose end_date falls in [on_date, on_date+window].

    Per currency. We use :func:`total_contract_value` rather than
    :func:`monthly_cost` because the procurement question is "how much
    does it cost to renew these for another term?" — not "what's the
    monthly equivalent?".
    """
    if on_date is None:
        on_date = date.today()
    cutoff = on_date + timedelta(days=window_days)

    qs = Contract.objects.filter(end_date__gte=on_date, end_date__lte=cutoff).only(
        "recurring_cost", "one_time_cost", "billing_period", "term_months", "currency"
    )

    totals = defaultdict(lambda: ZERO)
    for contract in qs:
        totals[contract.currency] += total_contract_value(contract)
    return dict(totals)


def spend_by_vendor(*, on_date=None, limit=10):
    """Top vendors by current monthly spend.

    Returns a list of ``(provider, monthly_total, currency)`` tuples,
    sorted descending by monthly total within each currency. Different
    currencies are NOT mixed — a vendor billing in EUR and a vendor billing
    in USD appear as separate entries even if "the EUR one" objectively
    costs more after FX conversion.

    ``limit`` caps the result so dashboard panels stay scannable; pass
    ``limit=None`` for the full sorted list.
    """
    if on_date is None:
        on_date = date.today()

    rollup = defaultdict(lambda: ZERO)  # (provider, currency) → monthly
    qs = (
        _active_contracts_qs(on_date)
        .select_related("provider")
        .only("recurring_cost", "billing_period", "currency", "provider__id", "provider__name")
    )
    for contract in qs:
        rollup[(contract.provider, contract.currency)] += monthly_cost(contract)

    rows = [(provider, total, currency) for (provider, currency), total in rollup.items()]
    rows.sort(key=lambda row: row[1], reverse=True)
    if limit is not None:
        rows = rows[:limit]
    return rows


def coverage_gap_count():
    """Lightweight count of Devices that have no direct ContractAssignment.

    Used by CostReportJob's summary line. This is a *direct-only* count
    (it does NOT walk the Tenant/Location ancestry) because the full
    transitive walk requires per-Device Python iteration and is too slow
    to embed in a recurring report. Operators wanting the transitive
    answer should run ``CoverageGapJob`` instead.
    """
    from nautobot.dcim.models import Device

    covered_ids = (
        Contract.objects.filter(end_date__gte=date.today()).values_list("assignments__object_id", flat=True).distinct()
    )
    # Devices not in the covered_ids list count as gaps.
    return Device.objects.exclude(id__in=covered_ids).aggregate(n=Count("id"))["n"]
