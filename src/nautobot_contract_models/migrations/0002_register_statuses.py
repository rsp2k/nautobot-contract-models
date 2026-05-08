"""Register Active / Expired / Cancelled / Pending Status records and bind to our content types.

This is the canonical Nautobot pattern for plugins that need their own status
vocabulary: rather than hardcoding choices on the model, we let operators see
and edit the Status records via the Nautobot admin UI. The plugin ships with
sensible defaults; operators can add more (e.g. "In Negotiation", "Paid",
"Disputed") as needed.

The migration is idempotent — running it multiple times (e.g. after a hot
fix to the schema) won't duplicate Status records, and content-type bindings
are added via the M2M ``add()`` which silently no-ops on duplicates.
"""

from django.db import migrations

# Status name -> (description, hex color) for the records we ship.
# Colors mirror Nautobot's built-in palette so the UI looks consistent.
DEFAULT_STATUSES = {
    "Active": ("Currently in force.", "4caf50"),
    "Expired": ("End date has passed; not renewed.", "f44336"),
    "Cancelled": ("Terminated before the end date.", "111111"),
    "Pending": ("Signed but not yet active, or awaiting countersignature.", "ffeb3b"),
}

# Models in this plugin that take a Status. ContractAssignment is BaseModel
# (no Status field), so it's not in this list.
TARGET_MODELS = ["contract", "invoice"]


def populate_statuses(apps, schema_editor):
    """Create Status records and bind to Contract + Invoice content types."""
    # ContentType rows are created lazily by post_migrate, which fires AFTER
    # the whole `migrate` command — too late for us. Force-create them now.
    from django.apps import apps as global_apps
    from django.contrib.contenttypes.management import create_contenttypes

    app_config = global_apps.get_app_config("nautobot_contract_models")
    create_contenttypes(app_config, verbosity=0)

    Status = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")

    target_cts = [ContentType.objects.get(app_label="nautobot_contract_models", model=model) for model in TARGET_MODELS]

    for name, (description, color) in DEFAULT_STATUSES.items():
        status, _created = Status.objects.get_or_create(
            name=name,
            defaults={"description": description, "color": color},
        )
        # add() is idempotent for M2M membership.
        for ct in target_cts:
            status.content_types.add(ct)


def unbind_statuses(apps, schema_editor):
    """Reverse op: remove our content types from the Status records.

    Don't delete the Status records themselves — they may be in use by other
    apps (Active is shared with Device, Circuit, etc.). Only unbind ours.
    """
    Status = apps.get_model("extras", "Status")
    ContentType = apps.get_model("contenttypes", "ContentType")

    target_cts = [ContentType.objects.get(app_label="nautobot_contract_models", model=model) for model in TARGET_MODELS]

    for name in DEFAULT_STATUSES:
        try:
            status = Status.objects.get(name=name)
        except Status.DoesNotExist:
            continue
        for ct in target_cts:
            status.content_types.remove(ct)


class Migration(migrations.Migration):
    """Bind plugin status vocabulary at install time."""

    dependencies = [
        ("nautobot_contract_models", "0001_initial"),
        ("extras", "0142_remove_scheduledjob_approval_required"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(populate_statuses, unbind_statuses),
    ]
