import datetime as dt
import itertools
import sys

from django.contrib.admin.utils import NestedObjects
from django.core import serializers
from django.core.management.base import BaseCommand

from eas.api import models


def serialize_public_draws(file_):
    backup_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=10)
    backup_ids = set()
    collector = NestedObjects(using="default")
    for result in models.Result.objects.filter(schedule_date__gt=backup_cutoff):
        draw = result.draw
        if draw.id in backup_ids:
            continue
        collector.collect([draw])
        backup_ids.add(draw.id)
    all_draw_objects = itertools.chain.from_iterable(collector.data.values())
    serializers.serialize("json", list(all_draw_objects), stream=file_)


def deserialize_draws(file_):
    objects = list(
        serializers.deserialize("json", file_, handle_forward_references=True)
    )
    draws = filter(lambda o: isinstance(o, models.BaseDraw), objects)
    non_draws = filter(lambda o: not isinstance(o, models.BaseDraw), objects)
    for obj in itertools.chain(draws, non_draws):
        try:
            obj.save(0)
        except Exception as e:  # pragma: no cover
            print(f"Failed to load {obj!r}: {e!r}")


class Command(BaseCommand):  # pragma: no cover
    help = "Loads or dumps data to backup from the database"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")
        dump_parser = subparsers.add_parser("dump")
        load_parser = subparsers.add_parser("load")
        dump_parser.add_argument("target_file", nargs="?")
        load_parser.add_argument("target_file", nargs="?")

    def handle(self, *args, **options):
        if options["action"] == "dump":
            if options.get("target_file"):
                stream = open(options["target_file"], "w")
            else:
                stream = sys.stdout
            serialize_public_draws(stream)
        elif options["action"] == "load":
            if options.get("target_file"):
                stream = open(options["target_file"])
            else:
                stream = sys.stdin
            deserialize_draws(stream)
