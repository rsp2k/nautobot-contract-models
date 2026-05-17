"""iCal export + per-user token management — Phase 20.

Two views in one module because they share the :class:`ICalAccessToken`
model and the URL token is the whole reason for the regenerate page.

Auth model — two stages, deliberately:
    1. Session: ``request.user.is_authenticated`` (browser users following
       a link from inside Nautobot). Standard Django.
    2. URL token: ``?token=<32-char-secret>``. Used by calendar clients
       (Outlook / Google / iCloud) that subscribe to a feed URL and re-fetch
       it on a schedule without carrying session cookies.

A request that has neither a valid session nor a matching token gets a 401.

We deliberately do NOT reuse Nautobot's REST API tokens; those grant full
account access and a leaked subscription URL would compromise the whole
account. See :class:`ICalAccessToken` for the rationale.

iCal format: hand-rolled RFC 5545. Date-only events (``DTSTART;VALUE=DATE``)
mean we don't fight with timezones — all-day events render the same in every
calendar client regardless of the viewer's locale.
"""

from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import View

from nautobot_contract_models.models import Contract, ICalAccessToken

ICAL_PRODID = "-//Nautobot//nautobot-contract-models//EN"


def _fold_line(line, max_len=75):
    """RFC 5545 line folding: long lines must be split at 75 octets with leading whitespace on continuations."""
    if len(line.encode("utf-8")) <= max_len:
        return line
    chunks = []
    while len(line.encode("utf-8")) > max_len:
        # Walk back from max_len to find a safe split point (don't split mid-multibyte char)
        cut = max_len
        while len(line[:cut].encode("utf-8")) > max_len:
            cut -= 1
        chunks.append(line[:cut])
        line = " " + line[cut:]  # continuation line starts with a space
    chunks.append(line)
    return "\r\n".join(chunks)


def _ical_escape(text):
    r"""RFC 5545 5.1: escape ``,``, ``;``, ``\``, and newlines inside property values."""
    if text is None:
        return ""
    return (
        str(text).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n").replace("\r", "")
    )


def _build_ical(contracts, *, host):
    """Render an RFC-5545 VCALENDAR with one VEVENT per contract end_date.

    Active contracts (end_date >= today) emit a VEVENT for end_date. Future-
    starting contracts also emit a VEVENT for start_date so newly-signed
    contracts about-to-begin show up in the operator's calendar.
    """
    today = date.today()
    now_stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{ICAL_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        _fold_line(f"X-WR-CALNAME:{_ical_escape('Nautobot Contracts')}"),
        _fold_line(f"X-WR-CALDESC:{_ical_escape('Contract renewal deadlines from nautobot-contract-models.')}"),
    ]

    for contract in contracts:
        provider = contract.provider.name if contract.provider_id else "—"
        cost_blurb = f"{contract.recurring_cost} {contract.currency} {contract.billing_period}."

        # End-date event (the renewal deadline). Always emit for active contracts.
        if contract.end_date >= today:
            end_dt = contract.end_date.strftime("%Y%m%d")
            summary_end = f"Contract renewal: {contract.name} ({provider})"
            description_end = f"Renewal deadline. {cost_blurb}"
            lines += [
                "BEGIN:VEVENT",
                _fold_line(f"UID:contract-end-{contract.pk}@{host}"),
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{end_dt}",
                _fold_line(f"SUMMARY:{_ical_escape(summary_end)}"),
                _fold_line(f"DESCRIPTION:{_ical_escape(description_end)}"),
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]

        # Start-date event — only for not-yet-started contracts so the
        # calendar surfaces upcoming kickoffs without cluttering historical view.
        if contract.start_date > today:
            start_dt = contract.start_date.strftime("%Y%m%d")
            summary_start = f"Contract starts: {contract.name} ({provider})"
            description_start = f"Contract begins. {cost_blurb}"
            lines += [
                "BEGIN:VEVENT",
                _fold_line(f"UID:contract-start-{contract.pk}@{host}"),
                f"DTSTAMP:{now_stamp}",
                f"DTSTART;VALUE=DATE:{start_dt}",
                _fold_line(f"SUMMARY:{_ical_escape(summary_start)}"),
                _fold_line(f"DESCRIPTION:{_ical_escape(description_start)}"),
                "TRANSP:TRANSPARENT",
                "END:VEVENT",
            ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


class ContractICalExportView(View):
    """``/plugins/contracts/contracts.ics`` — iCal feed of all active contracts.

    Returns 401 if neither session nor URL-token authenticates. 403 if the
    authenticated user lacks ``view_contract`` permission.
    """

    def _resolve_user(self, request):
        """Return the user authenticated by either session or ?token=, or None."""
        if request.user.is_authenticated:
            return request.user

        token_value = request.GET.get("token", "").strip()
        if not token_value:
            return None
        try:
            token = ICalAccessToken.objects.select_related("user").get(token=token_value)
        except ICalAccessToken.DoesNotExist:
            return None

        # Touch last_used_at so operators can see the feed is being polled.
        token.last_used_at = timezone.now()
        token.save(update_fields=["last_used_at"])
        return token.user

    def get(self, request):
        """Render the calendar; 401 / 403 on auth failure."""
        user = self._resolve_user(request)
        if user is None:
            return HttpResponse(
                "Authentication required. Either sign in via the browser or append ?token=<your-token> "
                "(get your token at /plugins/contracts/ical-token/).",
                status=401,
                content_type="text/plain",
            )
        if not user.has_perm("nautobot_contract_models.view_contract"):
            return HttpResponse(
                "Permission denied. You do not have view_contract permission.",
                status=403,
                content_type="text/plain",
            )

        contracts = (
            Contract.objects.select_related("provider").filter(end_date__gte=date.today()).order_by("end_date", "name")
        )
        body = _build_ical(contracts, host=request.get_host().split(":")[0])
        response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = 'inline; filename="nautobot-contracts.ics"'
        return response


class ICalTokenManageView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """``/plugins/contracts/ical-token/`` — display current token + regenerate.

    Auto-creates the token on first GET so operators don't have to think
    about an extra step. ``POST regenerate=1`` rotates the secret;
    ``POST delete=1`` removes the token (revoking access until next GET).
    """

    permission_required = "nautobot_contract_models.view_contract"
    template_name = "nautobot_contract_models/ical_token.html"

    def _get_or_create_token(self, user):
        """Returns (token_obj, created_bool). Auto-create on first call per user."""
        token, created = ICalAccessToken.objects.get_or_create(user=user)
        return token, created

    def _render(self, request, token, created=False, just_regenerated=False):
        """Render the manage page with the subscription URL pre-built."""
        from django.shortcuts import render

        ical_url = request.build_absolute_uri(reverse("plugins:nautobot_contract_models:contract_ical_export"))
        subscription_url = f"{ical_url}?token={token.token}"
        return render(
            request,
            self.template_name,
            {
                "token": token,
                "subscription_url": subscription_url,
                "ical_url": ical_url,
                "created": created,
                "just_regenerated": just_regenerated,
            },
        )

    def get(self, request):
        """Show the user's token + subscription URL. Auto-create on first visit."""
        token, created = self._get_or_create_token(request.user)
        return self._render(request, token, created=created)

    def post(self, request):
        """Rotate or delete the token; render the result page."""
        action = request.POST.get("action", "").strip()
        if action == "regenerate":
            token, _ = self._get_or_create_token(request.user)
            token.regenerate()
            return self._render(request, token, just_regenerated=True)
        if action == "delete":
            ICalAccessToken.objects.filter(user=request.user).delete()
            token, _ = self._get_or_create_token(request.user)
            return self._render(request, token, just_regenerated=True)
        raise Http404("Unknown action")
