import random
from functools import partial

import factory as fb

from .. import models

Faker = partial(fb.Faker, locale="es_ES")  # pylint: disable=invalid-name


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
        prizes = kwargs.pop('prizes')
        participants = kwargs.pop('participants')
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

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop('participants')
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw


class GroupsFactory(BaseDrawFactory):
    class Meta:
        model = "api.Groups"

    participants = fb.List([
        dict(name=name) for name in
        ["julian", "pepe", "rico", "maria", "susana", "clara"]
    ])
    number_of_groups = 2

    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        participants = kwargs.pop('participants')
        manager = cls._get_manager(model_class)
        draw = manager.create(*args, **kwargs)
        for participant in participants:
            models.Participant.objects.create(**participant, draw=draw)

        return draw


class SpinnerFactory(BaseDrawFactory):
    class Meta:
        model = "api.Spinner"
