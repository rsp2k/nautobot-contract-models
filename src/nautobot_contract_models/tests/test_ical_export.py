"""Tests for the iCal export view and ICalAccessToken model — Phase 20.

Two surfaces:
1. ``/plugins/contracts/contracts.ics`` — feed generation + auth gating
2. ``/plugins/contracts/ical-token/`` — token management UI

We exercise the auth ladder explicitly: anonymous + no-token, anonymous +
bad-token, anonymous + valid-token, authenticated-no-perm, authenticated-perm.
The hand-rolled RFC 5545 body is parsed by simple line-startswith checks
rather than a full iCal parser — keeps tests dependency-free.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from nautobot.core.testing import TestCase

from nautobot_contract_models.models import ICalAccessToken

from .fixtures import make_contract, make_provider

User = get_user_model()


class ICalAccessTokenModelTests(TestCase):
    """Token defaults, uniqueness, and regenerate() behavior."""

    def test_get_or_create_yields_a_token(self):
        token, created = ICalAccessToken.objects.get_or_create(user=self.user)
        self.assertTrue(created)
        self.assertGreaterEqual(len(token.token), 32)

    def test_regenerate_rotates_secret_and_resets_last_used(self):
        token = ICalAccessToken.objects.create(user=self.user)
        old_secret = token.token
        token.last_used_at = None
        token.save()
        new_secret = token.regenerate()
        self.assertNotEqual(old_secret, new_secret)
        token.refresh_from_db()
        self.assertEqual(token.token, new_secret)
        self.assertIsNone(token.last_used_at)

    def test_one_token_per_user(self):
        ICalAccessToken.objects.create(user=self.user)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ICalAccessToken.objects.create(user=self.user)


class ICalExportViewAuthTests(TestCase):
    """The auth ladder for /plugins/contracts/contracts.ics."""

    url = reverse("plugins:nautobot_contract_models:contract_ical_export")
    user_permissions = ("nautobot_contract_models.view_contract",)

    def setUp(self):
        super().setUp()
        self.provider = make_provider(name="iCal Vendor")
        # One future-expiry contract to ensure at least one VEVENT in the feed.
        self.contract = make_contract(
            name="iCal Test Contract",
            provider=self.provider,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() + timedelta(days=180),
        )

    def test_unauthenticated_no_token_returns_401(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_bad_token_returns_401(self):
        self.client.logout()
        response = self.client.get(self.url, {"token": "this-is-not-a-real-token"})
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_valid_token_returns_calendar(self):
        self.client.logout()
        token = ICalAccessToken.objects.create(user=self.user)
        # user_permissions class-attr already grants view_contract.
        response = self.client.get(self.url, {"token": token.token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")
        self.assertIn("BEGIN:VCALENDAR", response.content.decode("utf-8"))

    def test_authenticated_session_returns_calendar(self):
        # TestCase already logs in self.user with full perms.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/calendar; charset=utf-8")

    def test_authenticated_without_view_permission_returns_403(self):
        # Nautobot grants permissions via ObjectPermission rows (see
        # add_permissions in nautobot.core.testing.mixins), NOT via Django's
        # standard `user.user_permissions`. To revoke for this test we
        # remove the user from every ObjectPermission they're attached to.
        from nautobot.users.models import ObjectPermission

        self.user.is_superuser = False
        self.user.save()
        for op in ObjectPermission.objects.filter(users=self.user):
            op.users.remove(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class ICalExportContentTests(TestCase):
    """Verify the rendered VCALENDAR body shape — UID, DTSTART, SUMMARY, etc."""

    url = reverse("plugins:nautobot_contract_models:contract_ical_export")
    user_permissions = ("nautobot_contract_models.view_contract",)

    def setUp(self):
        super().setUp()
        self.provider = make_provider(name="Body Test Vendor")
        # Active contract (end_date in the future) — should generate a VEVENT.
        self.active = make_contract(
            name="Active Contract",
            provider=self.provider,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=60),
            recurring_cost=Decimal("250.00"),
        )
        # Future-starting contract — should generate TWO VEVENTs (start and end).
        self.future = make_contract(
            name="Future Contract",
            provider=self.provider,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=395),
        )
        # Already-expired contract — should generate ZERO VEVENTs.
        self.expired = make_contract(
            name="Expired Contract",
            provider=self.provider,
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=30),
        )

    def _get_body(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.content.decode("utf-8")

    def test_feed_includes_active_contract_end_event(self):
        body = self._get_body()
        self.assertIn(f"contract-end-{self.active.pk}", body)
        self.assertIn(self.active.end_date.strftime("%Y%m%d"), body)
        self.assertIn("Active Contract", body)

    def test_feed_includes_future_contract_start_and_end_events(self):
        body = self._get_body()
        self.assertIn(f"contract-end-{self.future.pk}", body)
        self.assertIn(f"contract-start-{self.future.pk}", body)

    def test_feed_excludes_expired_contracts(self):
        body = self._get_body()
        self.assertNotIn(f"contract-end-{self.expired.pk}", body)

    def test_feed_has_required_vcalendar_envelope(self):
        body = self._get_body()
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("VERSION:2.0", body)
        self.assertIn("PRODID:", body)
        self.assertIn("END:VCALENDAR", body)


class ICalTokenManageViewTests(TestCase):
    """The /ical-token/ page: GET auto-creates, POST regenerate/delete."""

    url = reverse("plugins:nautobot_contract_models:ical_token_manage")
    user_permissions = ("nautobot_contract_models.view_contract",)

    def test_get_auto_creates_token(self):
        self.assertFalse(ICalAccessToken.objects.filter(user=self.user).exists())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ICalAccessToken.objects.filter(user=self.user).exists())

    def test_post_regenerate_rotates_token(self):
        token = ICalAccessToken.objects.create(user=self.user)
        old_secret = token.token
        response = self.client.post(self.url, {"action": "regenerate"})
        self.assertEqual(response.status_code, 200)
        token.refresh_from_db()
        self.assertNotEqual(token.token, old_secret)

    def test_post_delete_then_recreate(self):
        old_token = ICalAccessToken.objects.create(user=self.user)
        old_secret = old_token.token
        response = self.client.post(self.url, {"action": "delete"})
        self.assertEqual(response.status_code, 200)
        # After delete, a new token exists with a different secret.
        new_token = ICalAccessToken.objects.get(user=self.user)
        self.assertNotEqual(new_token.token, old_secret)
