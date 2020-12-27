import datetime as dt

from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand

from eas.api import models

MODELS = [
    models.Coin,
    models.Groups,
    models.Letter,
    models.Link,
    models.Lottery,
    models.Raffle,
    models.RandomNumber,
    models.Spinner,
]

DEFAULT_DAYS_TO_KEEP = 90


def get_latest_usage(draw):
    results = draw.results.all()
    if not results:
        return draw.created_at
    return max(
        result.created_at
        if result.schedule_date is None
        else max(result.created_at, result.schedule_date)
        for result in results
    )


def delete_old_records(days_to_keep=DEFAULT_DAYS_TO_KEEP, dry_run=False):
    now = dt.datetime.now(dt.timezone.utc)
    usage_cutoff = now - dt.timedelta(days=days_to_keep)
    deleted_records = 0
    for model in MODELS:
        for draw in model.objects.filter(created_at__lte=usage_cutoff):
            latest_usage = get_latest_usage(draw)
            if latest_usage < usage_cutoff:
                deleted_records += 1
                if not dry_run:
                    draw.delete()
    return deleted_records


class Command(BaseCommand):  # pragma: no cover
    help = "Purges old data from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "days-to-keep", nargs="?", type=int, default=DEFAULT_DAYS_TO_KEEP
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        deleted_records = delete_old_records(
            options["days-to-keep"], options["dry_run"]
        )
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_records} draws"))
