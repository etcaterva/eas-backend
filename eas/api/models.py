"""Models of the objects used in EAS"""
import random
import uuid
import datetime as dt
import itertools

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
        return self._generate_result(
            value=self.generate_result(),
            draw=self,
        )

    def schedule_toss(self, target_date):
        return self._generate_result(
            schedule_date=target_date,
            draw=self,
        )

    def _generate_result(self, **kwargs):
        if self.results.count() >= self.RESULTS_LIMIT:
            self.results.order_by("created_at").first().delete()
        result_obj = Result(
            **kwargs
        )
        result_obj.save()  # Should we really save here???
        return result_obj

    def resolve_scheduled_results(self):
        """Resolves all scheduled results in the past"""
        for result in self.results.filter(
                schedule_date__lte=dt.datetime.now(dt.timezone.utc)):
            if result.value is None:
                result.value = self.generate_result()
                result.save()

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
    """Represents a result of tossing a draw.

    The value of the result is stored in the value column as JSON. If
    the toss is scheduled for a future date, schedule_date will be set
    to that date and value will be null.
    """
    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE,
                             related_name="results")
    value = JSONField(null=True)
    schedule_date = models.DateTimeField(null=True)

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)


class RandomNumber(BaseDraw):
    range_min = models.IntegerField()
    range_max = models.IntegerField()
    number_of_results = models.PositiveIntegerField(default=1)

    def generate_result(self):
        return [random.randint(self.range_min, self.range_max)
                for _ in range(self.number_of_results)]


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


class PrizesMixin:
    """Mixin to add a prizes attribute and retrieve prizes related to a draw"""

    SERIALIZE_FIELDS = ['id', 'name', 'url']  # Fields to serialize in a result

    @property
    def prizes(self):
        return Prize.objects.filter(draw=self)


class ParticipantsMixin:
    """Mixin to add an attribute to retrieve participants"""

    SERIALIZE_FIELDS = ['id', 'name', 'facebook_id']  # Fields to serialize in a result

    @property
    def participants(self):
        return Participant.objects.filter(draw=self)


class Raffle(BaseDraw, PrizesMixin, ParticipantsMixin):
    def generate_result(self):
        result = []
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS))
        random.shuffle(participants)
        for prize, winner in zip(
                self.prizes.values(*PrizesMixin.SERIALIZE_FIELDS),
                participants):
            result.append({
                "prize": prize,
                "participant": winner,
            })
        return result


class Lottery(BaseDraw, ParticipantsMixin):
    def generate_result(self):
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS))
        winner = random.choice(participants)
        return [winner]


class Groups(BaseDraw, ParticipantsMixin):
    number_of_groups = models.PositiveIntegerField(null=False)

    def generate_result(self):
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS))
        random.shuffle(participants)
        groups = [list() for _ in range(self.number_of_groups)]
        for group, participant in zip(itertools.cycle(groups), participants):
            group.append(participant)
        return groups
