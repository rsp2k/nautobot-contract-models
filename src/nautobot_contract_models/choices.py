"""Choice classes for the contract-models plugin.

Phase 7 introduces structured SLA / coverage / contract-type fields. We use
:class:`ChoiceSet` (Nautobot's native choice base) rather than free-text so
operators can filter by the value in list views, dashboards, and the API.

Each ChoiceSet's vocabulary is intentionally short — real-world SLAs and
contract categories cluster around a handful of values. If an operator's
contract doesn't fit, they fall back to the model's free-text ``description``
or ``comments`` fields.
"""

from nautobot.apps.choices import ChoiceSet


class ContractTypeChoices(ChoiceSet):
    """The kind of agreement this contract represents.

    Drives renewal-priority defaults and dashboard grouping. Operators
    choose the closest match; "other" is the catch-all for non-standard
    arrangements (consulting retainers, partnership agreements, etc.).
    """

    HARDWARE = "hardware"
    SOFTWARE = "software"
    SAAS = "saas"
    SERVICES = "services"
    MANAGED = "managed"
    SUPPORT = "support"
    WARRANTY = "warranty"
    OTHER = "other"

    CHOICES = (
        (HARDWARE, "Hardware Maintenance"),
        (SOFTWARE, "Software Subscription"),
        (SAAS, "SaaS Subscription"),
        (SERVICES, "Professional Services"),
        (MANAGED, "Managed Services"),
        (SUPPORT, "Vendor Support"),
        (WARRANTY, "Manufacturer Warranty"),
        (OTHER, "Other"),
    )


class CoverageHoursChoices(ChoiceSet):
    """When the vendor is contractually available to take a support call.

    These cover the vast majority of real-world support contracts. Phrases
    like "24x5xNBD" mean "answers calls 24 hours a day, 5 days a week, with
    next-business-day on-site response."
    """

    HOURS_24X7 = "24x7"
    HOURS_24X5 = "24x5"
    HOURS_BUSINESS = "business_hours"
    HOURS_8X5_NBD = "8x5_nbd"
    HOURS_BEST_EFFORT = "best_effort"

    CHOICES = (
        (HOURS_24X7, "24x7 — every day"),
        (HOURS_24X5, "24x5 — weekdays only"),
        (HOURS_BUSINESS, "Business hours (9-5 local)"),
        (HOURS_8X5_NBD, "8x5xNBD — business hours with next-business-day on-site"),
        (HOURS_BEST_EFFORT, "Best effort"),
    )


class ResponseTimeChoices(ChoiceSet):
    """Contractual response-time SLA — when the vendor must acknowledge / engage.

    "NBD" = next business day. "Best effort" means no enforceable SLA.
    """

    HOURS_1 = "1h"
    HOURS_2 = "2h"
    HOURS_4 = "4h"
    HOURS_8 = "8h"
    NBD = "nbd"
    BEST_EFFORT = "best_effort"

    CHOICES = (
        (HOURS_1, "1 hour"),
        (HOURS_2, "2 hours"),
        (HOURS_4, "4 hours"),
        (HOURS_8, "8 hours"),
        (NBD, "Next business day"),
        (BEST_EFFORT, "Best effort"),
    )


class RestorationTimeChoices(ChoiceSet):
    """Contractual time-to-restore SLA — when service must be back up.

    Distinct from response time: a 4-hour response with NBD restoration is
    common — vendor engages quickly but parts may take a day to arrive.
    """

    HOURS_4 = "4h"
    HOURS_8 = "8h"
    HOURS_24 = "24h"
    NBD = "nbd"
    DAYS_2 = "2d"
    DAYS_5 = "5d"
    NONE = "none"

    CHOICES = (
        (HOURS_4, "4 hours"),
        (HOURS_8, "8 hours"),
        (HOURS_24, "24 hours"),
        (NBD, "Next business day"),
        (DAYS_2, "2 business days"),
        (DAYS_5, "5 business days"),
        (NONE, "No restoration SLA"),
    )


class BillingPeriodChoices(ChoiceSet):
    """Cadence at which ``recurring_cost`` is charged.

    Phase 8 introduces this so cost analytics can normalize across
    contracts. Without it, a $1,200 annual contract and a $1,200 monthly
    contract are indistinguishable at the schema level — aggregating the
    two would give a $2,400 monthly burn that's wrong by 12x.

    ``one_time`` flags contracts that aren't recurring at all — typically
    setup-fee-only or perpetual-license deals. The cost helpers fold those
    into ``total_contract_value`` rather than the burn-rate calculation.
    """

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    ONE_TIME = "one_time"

    CHOICES = (
        (MONTHLY, "Monthly"),
        (QUARTERLY, "Quarterly"),
        (SEMIANNUAL, "Every 6 months"),
        (ANNUAL, "Annual"),
        (ONE_TIME, "One-time / non-recurring"),
    )
