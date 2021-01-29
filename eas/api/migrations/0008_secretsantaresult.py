# Generated by Django 2.2.13 on 2021-01-28 22:26

from django.db import migrations, models

import eas.api.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "007_drop_pk_like_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecretSantaResult",
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
                ("source", models.CharField(max_length=100)),
                ("target", models.CharField(max_length=100)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
