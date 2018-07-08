"""Models of the objects used in EAS"""
import random
import uuid

from django.db import models
from jsonfield import JSONField


def create_id():
    return str(uuid.uuid4())


class BaseModel(models.Model):
    """Base Model for all the models"""
    class Meta:
        abstract = True

    id = models.CharField(max_length=64, default=create_id,
                          primary_key=True, null=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)


class BaseDraw(BaseModel):
    """Base Model for all the draws"""
    RESULTS_LIMIT = 50  # Max number of results to keep

    private_id = models.CharField(max_length=64, default=create_id,
                                  unique=True, null=False, editable=False)
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


class ClientDrawMetaData(BaseModel):
    """Opaque Meta data about an object that clients can store"""
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE, related_name="metadata")
    client = models.CharField(max_length=100)
    key = models.CharField(max_length=100, null=False, unique=False)
    value = models.TextField()


class Result(BaseModel):
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


class Participant(BaseModel):
    """Models an user that interacts in a draw

    User in raffles, tournaments, etc.

    Even if it links to a draw, not all draws support it.
    """
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE)

    name = models.TextField(null=False)
    facebook_id = models.CharField(max_length=100, null=True)

    def __repr__(self):  # pragma: nocover
        return "<%s  %r(%r)>" % (self.__class__.__name__, self.name, self.id)


class Prize(BaseModel):
    """A prize assigned to a draw

    Even if it links to a draw, not all draws support it.
    """
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE)

    name = models.TextField(null=False)
    url = models.URLField(null=True)

    def __repr__(self):  # pragma: nocover
        return "<%s  %r(%r)>" % (self.__class__.__name__, self.name, self.id)


class PricesMixin:
    """Mixin to add a prizes attribute and retrieve prizes related to a draw"""
    @property
    def prizes(self):
        return Prize.objects.filter(draw=self)


class ParticipantsMixin:
    """Mixin to add an attribute to retrieve participants"""
    @property
    def participants(self):
        return Participant.objects.filter(draw=self)


class Raffle(BaseDraw, PricesMixin, ParticipantsMixin):
    def generate_result(self):
        result = []
        participants = list(self.participants.all())
        random.shuffle(participants)
        for prize, winner in zip(self.prizes, participants):
            result.append({
                "prize": {"id": prize.id, "name": prize.name},
                "participant": {"id": winner.id, "name": winner.name}
            })
        return result
