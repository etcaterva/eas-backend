# Generated by Django 2.2.2 on 2019-10-05 15:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="participant",
            unique_together={("draw", "facebook_id")},
        ),
    ]
