"""Models of the objects used in EAS"""
import random
import uuid

from django.db import models


def create_id():
    return str(uuid.uuid4())


class BaseDraw(models.Model):
    """Base Model for all the draws"""
    RESULT_CLASS = None  # set on child
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
        result_obj = self.RESULT_CLASS(  # pylint: disable=not-callable
            value=result,
            draw=self,
        )
        result_obj.save()  # Should we really save here???
        return result_obj

    @property
    def results(self):
        return self.RESULT_CLASS.objects.filter(draw__id=self.id)

    def __repr__(self):  # pragma: nocover
        return "<%s  %r>" % (self.__class__.__name__, self.id)


class BaseResult(models.Model):
    class Meta:
        abstract = True

    created_at = models.DateTimeField(auto_now_add=True, editable=False,
                                      null=False)
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE)
    value = None  # To be set by child

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)


class RandomNumberResult(BaseResult):
    value = models.IntegerField()


class RandomNumber(BaseDraw):
    RESULT_CLASS = RandomNumberResult

    range_min = models.IntegerField()
    range_max = models.IntegerField()

    def generate_result(self):
        return random.randint(self.range_min, self.range_max)
