import datetime as dt
import random
from functools import partial

import factory as fb

from .. import models

Faker = partial(fb.Faker, locale="es_ES")  # pylint: disable=invalid-name
NOW = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)
NOW = NOW.replace(microsecond=0)
HOUR_1 = dt.timedelta(hours=1)


class BaseDrawFactory(fb.django.DjangoModelFactory):
    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    title = Faker("sentence")
    description = Faker("text")


class MetadataFactory(fb.django.DjangoModelFactory):
    class Meta:
        model = "api.ClientDrawMetadata"

    client = "webapp"
    key = Faker("sentence")
    value = Faker("sentence")
    draw = fb.SubFactory(BaseDrawFactory)


class RandomNumberFactory(BaseDrawFactory):
    class Meta:
        model = "api.RandomNumber"

    range_min = random.randint(0, 49)
    range_max = random.randint(50, 100)
    number_of_results = 1
    allow_repeated_results = False


class PrizeFactory(fb.django.DjangoModelFactory):
    class Meta:
        model = "api.Prize"

    name = fb.Faker("sentence")


class RaffleFactory(BaseDrawFactory):
    class Meta:
        model = "api.Raffle"

    prizes = fb.List([dict(name="cupcake"), dict(name="laptop")])
    participants = fb.List([dict(name="raul"), dict(name="juian")])

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        prizes = kwargs.pop("prizes")
        participants = kwargs.pop("participants")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for prize in prizes:
            models.Prize.objects.create(**prize, draw=draw)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw


class LotteryFactory(BaseDrawFactory):
    class Meta:
        model = "api.Lottery"

    participants = fb.List([dict(name="raul"), dict(name="juian")])
    number_of_results = 1

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop("participants")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw


class GroupsFactory(BaseDrawFactory):
    class Meta:
        model = "api.Groups"

    participants = fb.List(
        [
            dict(name=name)
            for name in ["julian", "pepe", "rico", "maria", "susana", "clara"]
        ]
    )
    number_of_groups = 2

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop("participants")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw


class TournamentFactory(BaseDrawFactory):
    class Meta:
        model = "api.Tournament"

    participants = fb.List(
        [
            dict(name=name)
            for name in ["julian", "pepe", "rico", "maria", "susana", "clara"]
        ]
    )

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop("participants")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)
        return draw


class SpinnerFactory(BaseDrawFactory):
    class Meta:
        model = "api.Spinner"


class LetterFactory(BaseDrawFactory):
    class Meta:
        model = "api.Letter"

    number_of_results = 1
    allow_repeated_results = False


class CoinFactory(BaseDrawFactory):
    class Meta:
        model = "api.Coin"


class LinkFactory(BaseDrawFactory):
    class Meta:
        model = "api.Link"

    items_set1 = fb.List(["paco1", "gloria1", "pepe1"])
    items_set2 = fb.List(["david2", "pedro2", "jose2"])

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)


class InstagramFactory(BaseDrawFactory):
    class Meta:
        model = "api.Instagram"

    post_url = "https://www.instagram.com/p/ChbV971lYLW/"
    use_likes = False
    min_mentions = 0
    prizes = fb.List([dict(name="cupcake"), dict(name="laptop")])

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        prizes = kwargs.pop("prizes")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for prize in prizes:
            models.Prize.objects.create(**prize, draw=draw)

        return draw


class TiktokFactory(BaseDrawFactory):
    class Meta:
        model = "api.Tiktok"

    post_url = "https://www.tiktok.com/@spiderfish257/video/6744531482393545985?lang=en"
    min_mentions = 0
    prizes = fb.List([dict(name="cupcake"), dict(name="laptop")])

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        prizes = kwargs.pop("prizes")
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for prize in prizes:
            models.Prize.objects.create(**prize, draw=draw)

        return draw


class ShiftsFactory(BaseDrawFactory):
    class Meta:
        model = "api.Shifts"

    intervals = fb.List([])
    participants = fb.List(
        [dict(name="pedro"), dict(name="david"), dict(name="mario"), dict(name="jack")]
    )

    @staticmethod
    def _fill_empty_intervals(intervals, participants):
        if intervals:
            return
        for i in range(len(participants)):
            intervals.append(
                {"start_time": NOW + HOUR_1 * i, "end_time": NOW + HOUR_1 * (i + 1)},
            )

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        res = fb.build(dict, FACTORY_CLASS=cls, **kwargs)
        cls._fill_empty_intervals(res["intervals"], res["participants"])
        return res

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop("participants")
        intervals = kwargs.get("intervals")
        cls._fill_empty_intervals(intervals, participants)
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw
