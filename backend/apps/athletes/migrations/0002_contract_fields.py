"""Contract fields for athletes (Tabla 8 / data minimization).

Replaces the personal-data schema of ``0001_initial`` (``first_name``,
``last_name``, ``date_of_birth``) with the pseudonymous technical code of
the CADI contract (``athlete_id``, ``label``, ``group``,
``registered_at``) and moves the table to its logical name
``cadi_athlete``.

Existing rows are backfilled before the personal columns are dropped:

* ``athlete_id``  ← ``ATL-<pk:04d>`` (no personal data, reversible);
* ``label``       ← ``NULL``; names are personal data and are deliberately
                    not copied into the new pseudonymous record;
* ``registered_at`` ← today (the old birth date is intentionally NOT
                    kept: data minimization, Ley 1581 de 2012).
"""

from django.db import migrations, models
import django.utils.timezone


def backfill_contract_fields(apps, schema_editor):
    """Populate the new columns from the old ones, then drop the old ones."""
    Athlete = apps.get_model("athletes", "Athlete")
    for athlete in Athlete.objects.all():
        athlete.athlete_id = "ATL-{0:04d}".format(athlete.pk)
        athlete.label = None
        athlete.registered_at = django.utils.timezone.now().date()
        athlete.save(update_fields=["athlete_id", "label", "registered_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("athletes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="athlete",
            name="athlete_id",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="athlete",
            name="label",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="athlete",
            name="group",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name="athlete",
            name="registered_at",
            field=models.DateField(null=True),
        ),
        migrations.RunPython(backfill_contract_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="athlete",
            name="athlete_id",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name="athlete",
            name="registered_at",
            field=models.DateField(),
        ),
        migrations.RemoveField(model_name="athlete", name="first_name"),
        migrations.RemoveField(model_name="athlete", name="last_name"),
        migrations.RemoveField(model_name="athlete", name="date_of_birth"),
        migrations.AlterModelOptions(
            name="athlete",
            options={
                "verbose_name": "athlete",
                "verbose_name_plural": "athletes",
            },
        ),
        # The move to the logical table name ``cadi_athlete`` is tracked by
        # the autodetector as AlterModelTable in 0003_alter_athlete_table.
    ]
