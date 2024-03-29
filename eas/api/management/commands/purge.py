import datetime as dt

from django.core.management.base import BaseCommand

from eas.api import models

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
    for model in models.DRAW_TYPES:
        for draw in model.objects.filter(created_at__lte=usage_cutoff):
            latest_usage = get_latest_usage(draw)
            if latest_usage < usage_cutoff:
                deleted_records += 1
                if not dry_run:
                    draw.delete()
    for ss in models.SecretSantaResult.objects.filter(created_at__lte=usage_cutoff):
        deleted_records += 1
        ss.delete()
    for pc in models.PromoCode.objects.filter(created_at__lte=usage_cutoff):
        deleted_records += 1
        pc.delete()
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
