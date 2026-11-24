# Generated for individual athlete training sessions.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sprint_sessions", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TrainingSessionModel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField()),
                ("duration_minutes", models.PositiveSmallIntegerField()),
                ("training_type", models.CharField(max_length=120)),
                (
                    "attendance_status",
                    models.CharField(
                        choices=[
                            ("present", "Presente"),
                            ("absent", "Ausente"),
                            ("excused", "Justificada"),
                        ],
                        max_length=10,
                    ),
                ),
                ("coach", models.CharField(blank=True, default="", max_length=150)),
                ("location", models.CharField(blank=True, default="", max_length=150)),
                ("follow_up_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "athlete",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="training_sessions",
                        to="athletes.athlete",
                    ),
                ),
            ],
            options={
                "verbose_name": "training session",
                "verbose_name_plural": "training sessions",
                "db_table": "cadi_trainingsession",
                "ordering": ["-timestamp", "-id"],
            },
        ),
        migrations.AddField(
            model_name="sprintsessionmodel",
            name="training_session",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sprint_tests",
                to="sprint_sessions.trainingsessionmodel",
            ),
        ),
    ]
