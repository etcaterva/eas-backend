import datetime as dt
import itertools
import sys

import dateutil.parser
from django.contrib.admin.utils import NestedObjects
from django.core import serializers
from django.core.management.base import BaseCommand

from eas.api import models


def partition(pred, iterable):
    """Use a predicate to partition entries into true entries and false entries"""
    t1, t2 = itertools.tee(iterable)
    return filter(pred, t1), itertools.filterfalse(pred, t2)


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
    serializers.serialize("json", all_draw_objects, stream=file_)


def serialize_updated_delta(file_, since):
    backup_ids = set()
    collector = NestedObjects(using="default")
    for draw_type in models.DRAW_TYPES:
        for draw in draw_type.objects.filter(updated_at__gt=since):
            collector.collect([draw])
            backup_ids.add(draw.id)
    all_draw_objects = itertools.chain.from_iterable(collector.data.values())
    serializers.serialize("json", all_draw_objects, stream=file_)


def deserialize_draws(file_):
    objects = list(
        serializers.deserialize("json", file_, handle_forward_references=True)
    )
    base_draws, objects = partition(
        lambda o: type(o.object) == models.BaseDraw, objects
    )
    draws, non_draws = partition(
        lambda o: isinstance(o.object, models.BaseDraw), objects
    )
    for obj in itertools.chain(base_draws, draws, non_draws):
        try:
            obj.save()
        except Exception as e:  # pragma: no cover
            print(f"Failed to load {obj!r}: {e!r}")


class Command(BaseCommand):  # pragma: no cover
    help = "Loads or dumps data to backup from the database"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")
        dump_parser = subparsers.add_parser("dump")
        load_parser = subparsers.add_parser("load")
        delta_parser = subparsers.add_parser("delta")
        dump_parser.add_argument("target_file", nargs="?")
        load_parser.add_argument("target_file", nargs="?")
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1, minutes=5)
        delta_parser.add_argument(
            "--since",
            default=str(since),
            type=dateutil.parser.parse,
            help="Time start to backup draws. Defaults to 1h and 5m in the past from now.",
        )
        delta_parser.add_argument("target_file", nargs="?")

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
        if options["action"] == "delta":
            since = options["since"]
            if options.get("target_file"):
                stream = open(options["target_file"], "w")
            else:
                stream = sys.stdout
            serialize_updated_delta(stream, since)
