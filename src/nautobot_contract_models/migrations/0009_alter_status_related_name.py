# Namespace the reverse accessor on Contract.status and Invoice.status so
# our StatusField doesn't collide with nautobot-app-device-lifecycle's
# ContractLCM.status (both default to Status.contracts otherwise, which
# trips Django's fields.E304 system check and blocks Nautobot startup
# when both apps are installed).
#
# AlterField for a related_name change is a Python-level rename only —
# no SQL runs, no column changes. Safe and instant on any size database.

import django.db.models.deletion
import nautobot.extras.models.statuses
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_contract_models", "0008_costsnapshot"),
        ("extras", "0001_initial_part_1"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contract",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contract_models_contracts",
                to="extras.status",
            ),
        ),
        migrations.AlterField(
            model_name="invoice",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contract_models_invoices",
                to="extras.status",
            ),
        ),
    ]
