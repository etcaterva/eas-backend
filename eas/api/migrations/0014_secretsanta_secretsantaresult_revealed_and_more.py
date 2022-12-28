# Generated by Django 4.1.4 on 2022-12-25 14:33

import django.db.models.deletion
from django.db import migrations, models

import eas.api.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0013_remove_instagram_use_comments"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecretSanta",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=eas.api.models.create_id,
                        editable=False,
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="secretsantaresult",
            name="revealed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="secretsantaresult",
            name="draw",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="api.secretsanta",
            ),
        ),
    ]