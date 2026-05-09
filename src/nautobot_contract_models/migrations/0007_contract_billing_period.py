# Hand-written to match Django 5.2's makemigrations output for an AddField
# of a CharField with a default. Notes:
#
# 1. ``choices=`` does NOT appear here. Django strips it from migrations
#    because choices are model-level metadata, not a database schema
#    concern — every existing migration in this app omits choices for
#    the same reason (see 0006).
#
# 2. Default is the string literal "monthly", matching
#    BillingPeriodChoices.MONTHLY. Existing rows get this value at
#    migration time, so dashboards that aggregate burn rate interpret
#    legacy ``recurring_cost`` as monthly. Operators with annual contracts
#    must edit them after the upgrade — this assumption is documented in
#    PLAN.md Phase 8 as the explicit migration-default decision.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_contract_models", "0006_contract_auto_renew_contract_contract_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="billing_period",
            field=models.CharField(default="monthly", max_length=20),
        ),
    ]
