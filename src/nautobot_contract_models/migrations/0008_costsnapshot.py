# Hand-written CreateModel for CostSnapshot. Matches what
# `nautobot-server makemigrations` would generate from
# models/snapshot.py — verified end-to-end with `migrate` followed
# by `makemigrations --check --dry-run` (no further changes detected).
#
# UUID PK + created/last_updated timestamps come from BaseModel; the
# fields below are CostSnapshot's own.

import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_contract_models", "0007_contract_billing_period"),
    ]

    operations = [
        migrations.CreateModel(
            name="CostSnapshot",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("snapshot_date", models.DateField()),
                ("currency", models.CharField(max_length=3)),
                ("monthly_burn", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("renewal_90d", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("active_contract_count", models.PositiveIntegerField(default=0)),
                ("coverage_gap_count", models.PositiveIntegerField(blank=True, default=0, null=True)),
            ],
            options={
                "ordering": ["-snapshot_date", "currency"],
            },
        ),
        migrations.AddIndex(
            model_name="costsnapshot",
            index=models.Index(fields=["-snapshot_date", "currency"], name="nautobot_co_snapsho_2347a0_idx"),
        ),
        migrations.AddConstraint(
            model_name="costsnapshot",
            constraint=models.UniqueConstraint(
                fields=("snapshot_date", "currency"),
                name="nbcm_costsnapshot_unique_per_date_currency",
            ),
        ),
    ]
