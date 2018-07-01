"""Models of the objects used in EAS"""
import random
import uuid

from django.db import models


def create_id():
    return str(uuid.uuid4())


class BaseDraw(models.Model):
    """Base Model for all the draws"""
    _RESULT_LIMIT = 50  # Max number of results to keep

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
        if self.results.count() >= self._RESULT_LIMIT:
            self.results.order_by("created_at").first().delete()
        result = self.generate_result()
        result_obj = RandomNumberResult(
            value=result,
            draw=self,
        )
        result_obj.save()  # Should we really save here???
        return result_obj

    def __repr__(self):  # pragma: nocover
        return "<%s  %r>" % (self.__class__.__name__, self.id)


class BaseResult(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      null=False)
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE,
                             related_name="results")
    value = None  # To be set by child

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)


class RandomNumberResult(BaseResult):
    value = models.IntegerField()


class RandomNumber(BaseDraw):
    RESULT_CLASS = RandomNumberResult

    range_min = models.IntegerField()
    range_max = models.IntegerField()

    def generate_result(self):  # pragma: nocover
        return random.randint(self.range_min, self.range_max)
