from django.core.management.base import BaseCommand

from eas.api import models


def create_code():
    code = models.PromoCode()
    code.save()
    return code.code


def get_all_codes():
    return [c.code for c in models.PromoCode.objects.all()]


class Command(BaseCommand):  # pragma: no cover
    help = "Purges old data from the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "count",
            nargs="?",
            type=int,
            help="Number of codes to generate, leave empty to list existing.",
        )

    def handle(self, *args, **options):
        if not options["count"]:
            for code in get_all_codes():
                print(code)
            return
        for i in range(options["count"]):
            print(create_code())
