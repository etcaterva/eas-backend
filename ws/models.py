"""Models of the objects used in EAS"""
import random
import uuid

from django.db import models


class BaseModel(models.Model):
    """The base model for all tables, provides a basic metadata"""
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    def __repr__(self):  # pragma: nocover
        return "<%s  %r>" % (self.__class__.__name__, self.id)


class RandomNumber(BaseModel):
    _RESULT_LIMIT = 50  # Max number of results to keep

    private_id = models.CharField(max_length=64, default=uuid.uuid4,
                                  unique=True, null=False, editable=False)
    title = models.TextField(null=True)
    description = models.TextField(null=True)
    range_min = models.IntegerField()
    range_max = models.IntegerField()

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

    def generate_result(self):  # pragma: nocover
        return random.randint(self.range_min, self.range_max)


class RandomNumberResult(BaseModel):

    value = models.IntegerField()
    draw = models.ForeignKey(RandomNumber, on_delete=models.CASCADE,
                             related_name="results")

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)

