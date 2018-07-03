import random
from functools import partial

import factory as fb

Faker = partial(fb.Faker, locale="es_ES")  # pylint: disable=invalid-name


class BaseDrawFactory(fb.django.DjangoModelFactory):
    @classmethod
    def dict(cls, **kwargs):
        """Returns a dict rather than an object"""
        return fb.build(dict, FACTORY_CLASS=cls, **kwargs)

    title = Faker("sentence")
    description = Faker("text")


class RandomNumberFactory(BaseDrawFactory):
    class Meta:
        model = "api.RandomNumber"

    range_min = random.randint(0, 49)
    range_max = random.randint(50, 100)
