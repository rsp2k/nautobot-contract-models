"""ICalAccessToken — per-user secret for token-auth on the iCal export URL.

Phase 20 introduces this. Calendar clients (Outlook, Google Calendar, iCloud)
subscribe to a feed URL and re-fetch it periodically. They send a single GET
with whatever auth was in the original URL — they don't carry Django session
cookies. So a session-only protected URL stops syncing the moment the
operator's session expires.

The fix: in addition to session auth, support a per-user URL-param token
(``?token=<secret>``). Operators fetch their token from a dedicated profile
page, paste the full URL into their calendar app, and the feed keeps
working forever (or until they regenerate the token to revoke).

Why not reuse Nautobot's REST API tokens (``nautobot.users.models.Token``)?
    Two reasons:
    1. Those tokens are full account credentials — a calendar app that
       caches the URL has *full account access* if the token leaks. An
       iCal-specific token narrows the blast radius to "read calendar".
    2. Operators rotating REST API tokens shouldn't break their calendar
       subscriptions, and vice versa. Separate concerns, separate tokens.

Why BaseModel, not PrimaryModel:
    Tokens don't need ChangeLog / Relationships / Tags. They're internal
    plumbing, not first-class objects operators tag and group. BaseModel
    gives the UUID PK + timestamps we need.
"""

import secrets

from django.conf import settings
from django.db import models
from nautobot.core.models import BaseModel


def _generate_token():
    """32 URL-safe characters of entropy. Used both as the column default and as the regenerate-action source."""
    return secrets.token_urlsafe(24)


class ICalAccessToken(BaseModel):
    """One iCal access token per user; embedded in the subscription URL as ``?token=...``."""

    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="contract_models_ical_token",
        help_text="Owner of this token. Cascade-deletes with the user.",
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_token,
        help_text="Opaque URL-safe secret. Embedded in the subscription URL; regenerate to revoke.",
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Last time a calendar client successfully authenticated with this token. Updated on every iCal fetch."
        ),
    )

    class Meta:
        """Model metadata."""

        ordering = ["user__username"]

    def __str__(self):
        """Render as ``ICalAccessToken(user=alice)`` for debug / changelog purposes; never include the secret."""
        return f"ICalAccessToken(user={self.user.username})"

    def regenerate(self):
        """Rotate the secret in place; saves immediately so callers don't have to."""
        self.token = _generate_token()
        self.last_used_at = None
        self.save()
        return self.token
