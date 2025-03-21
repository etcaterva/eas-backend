# Generated by Django 4.2.16 on 2025-03-09 12:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0019_tiktok"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="secret_santa",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="_payments",
                to="api.secretsanta",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="draw",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="_payments",
                to="api.basedraw",
            ),
        ),
    ]
