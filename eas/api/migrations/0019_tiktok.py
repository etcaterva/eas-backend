# Generated by Django 4.1.6 on 2024-05-11 09:25

import django.db.models.deletion
from django.db import migrations, models

import eas.api.models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0018_alter_randomnumber_range_max"),
    ]

    operations = [
        migrations.CreateModel(
            name="Tiktok",
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
                ("post_url", models.URLField()),
                ("min_mentions", models.IntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
            bases=("api.basedraw", eas.api.models.PrizesMixin),
        ),
    ]
