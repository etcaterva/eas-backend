# Generated by Django 4.1.4 on 2022-12-29 10:25

import django.db.models.deletion
import jsonfield.fields
from django.db import migrations, models

import eas.api.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0014_secretsanta_secretsantaresult_revealed_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Shifts",
            fields=[
                (
                    "basedraw_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="api.basedraw",
                    ),
                ),
                ("intervals", jsonfield.fields.JSONField()),
            ],
            options={
                "abstract": False,
            },
            bases=("api.basedraw", eas.api.models.ParticipantsMixin),
        ),
    ]