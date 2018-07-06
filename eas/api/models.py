"""Models of the objects used in EAS"""
import random
import uuid

from django.db import models
from jsonfield import JSONField


def create_id():
    return str(uuid.uuid4())


class BaseDraw(models.Model):
    """Base Model for all the draws"""
    RESULTS_LIMIT = 50  # Max number of results to keep

    id = models.CharField(max_length=64, default=create_id,
                          primary_key=True, null=False, editable=False)
    private_id = models.CharField(max_length=64, default=create_id,
                                  unique=True, null=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    title = models.TextField(null=True)
    description = models.TextField(null=True)

    def toss(self):
        """Generates and saves a result"""
        if self.results.count() >= self.RESULTS_LIMIT:
            self.results.order_by("created_at").first().delete()
        result = self.generate_result()
        result_obj = Result(
            value=result,
            draw=self,
        )
        result_obj.save()  # Should we really save here???
        return result_obj

    def generate_result(self):  # pragma: no cover
        raise NotImplementedError()

    def __repr__(self):  # pragma: nocover
        return "<%s  %r>" % (self.__class__.__name__, self.id)


class ClientDrawMetaData(models.Model):
    """Opaque Meta data about an object that clients can store"""
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE, related_name="metadata")
    client = models.CharField(max_length=100)
    key = models.CharField(max_length=100, null=False, unique=False)
    value = models.TextField()


class Result(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      null=False)
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE,
                             related_name="results")
    value = JSONField()

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)


class RandomNumber(BaseDraw):
    range_min = models.IntegerField()
    range_max = models.IntegerField()

    def generate_result(self):
        return random.randint(self.range_min, self.range_max)
