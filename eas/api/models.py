"""Models of the objects used in EAS"""
import datetime as dt
import enum
import itertools
import random
import string
import uuid

from django.db import models
from jsonfield import JSONField


def create_id():
    return str(uuid.uuid4())


class BaseModel(models.Model):
    """Base Model for all the models"""

    class Meta:
        abstract = True

    id = models.CharField(
        max_length=64, default=create_id, primary_key=True, null=False, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)


class BaseDraw(BaseModel):
    """Base Model for all the draws"""

    RESULTS_LIMIT = 50  # Max number of results to keep

    private_id = models.CharField(
        max_length=64, default=create_id, unique=True, null=False, editable=False
    )
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
        result_obj = Result(**kwargs)
        result_obj.save()  # Should we really save here???
        return result_obj

    def resolve_scheduled_results(self):
        """Resolves all scheduled results in the past"""
        for result in self.results.filter(
            schedule_date__lte=dt.datetime.now(dt.timezone.utc)
        ):
            if result.value is None:
                result.value = self.generate_result()
                result.save()

    def generate_result(self):  # pragma: no cover
        raise NotImplementedError()

    def __repr__(self):  # pragma: nocover
        return "<%s  %r>" % (self.__class__.__name__, self.id)

    @property
    def payments(self):
        draw_payments = list(self._payments.all())
        result = []
        if any(payment.option_certified for payment in draw_payments if payment.payed):
            result.append(Payment.Options.CERTIFIED.value)
        if any(payment.option_adfree for payment in draw_payments if payment.payed):
            result.append(Payment.Options.ADFREE.value)
        if any(payment.option_support for payment in draw_payments if payment.payed):
            result.append(Payment.Options.SUPPORT.value)
        return result


class ClientDrawMetaData(BaseModel):
    """Opaque Meta data about an object that clients can store"""

    draw = models.ForeignKey(
        BaseDraw, on_delete=models.CASCADE, related_name="metadata"
    )
    client = models.CharField(max_length=100)
    key = models.CharField(max_length=100, null=False, unique=False)
    value = models.TextField()


class Result(BaseModel):
    """Represents a result of tossing a draw.

    The value of the result is stored in the value column as JSON. If
    the toss is scheduled for a future date, schedule_date will be set
    to that date and value will be null.
    """

    draw = models.ForeignKey(BaseDraw, on_delete=models.CASCADE, related_name="results")
    value = JSONField(null=True)
    schedule_date = models.DateTimeField(null=True)

    def __repr__(self):
        return "<%s  %r>" % (self.__class__.__name__, self.value)


class MultiResultMixin(models.Model):
    """Allows to generate multiple results in a single toss"""

    class Meta:
        abstract = True

    number_of_results = models.PositiveIntegerField(default=1)
    allow_repeated_results = models.BooleanField(default=True)

    def generate_result_item(self):  # pragma: nocover
        raise NotImplementedError()

    def generate_result(self):
        result = []
        for _ in range(self.number_of_results):
            while True:
                item = self.generate_result_item()
                if self.allow_repeated_results or item not in result:
                    result.append(item)
                    break
        return result


class RandomNumber(MultiResultMixin, BaseDraw):
    range_min = models.IntegerField()
    range_max = models.IntegerField()

    def generate_result_item(self):
        return random.randint(self.range_min, self.range_max)


class Letter(MultiResultMixin, BaseDraw):
    def generate_result_item(self):
        return random.choice(string.ascii_uppercase)


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

    SERIALIZE_FIELDS = ["id", "name", "url"]  # Fields to serialize in a result

    @property
    def prizes(self):
        return Prize.objects.filter(draw=self)


class ParticipantsMixin:
    """Mixin to add an attribute to retrieve participants"""

    SERIALIZE_FIELDS = ["id", "name", "facebook_id"]  # Fields to serialize in a result

    @property
    def participants(self):
        return Participant.objects.filter(draw=self)


class Raffle(BaseDraw, PrizesMixin, ParticipantsMixin):
    def generate_result(self):
        result = []
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS)
        )
        random.shuffle(participants)
        for prize, winner in zip(
            self.prizes.values(*PrizesMixin.SERIALIZE_FIELDS),
            itertools.cycle(participants),
        ):
            result.append(
                {
                    "prize": prize,
                    "participant": winner,
                }
            )
        return result


class Lottery(BaseDraw, ParticipantsMixin):
    number_of_results = models.PositiveIntegerField(default=1)

    def generate_result(self):
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS)
        )
        random.shuffle(participants)
        return participants[0 : self.number_of_results]


class Groups(BaseDraw, ParticipantsMixin):
    number_of_groups = models.PositiveIntegerField(null=False)

    def generate_result(self):
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS)
        )
        random.shuffle(participants)
        groups = [list() for _ in range(self.number_of_groups)]
        for group, participant in zip(itertools.cycle(groups), participants):
            group.append(participant)
        return groups


class Link(BaseDraw):
    items_set1 = JSONField(null=True)
    items_set2 = JSONField(null=True)

    def generate_result(self):
        items1 = list(self.items_set1)
        items2 = list(self.items_set2)
        random.shuffle(items1)
        random.shuffle(items2)
        return [{"element1": x, "element2": y} for x, y in zip(items1, items2)]


class Spinner(BaseDraw):
    def generate_result(self):
        return random.randint(0, 259)


class Coin(BaseDraw):
    OPTIONS = ["HEAD", "TAIL"]

    def generate_result(self):
        return [random.choice(self.OPTIONS)]


class SecretSantaResult(BaseModel):
    source = models.CharField(max_length=100)
    target = models.CharField(max_length=100)

    def __repr__(self):
        return "<%s  (%r,%r)>" % (self.__class__.__name__, self.source, self.target)

    def __str__(self):
        return repr(self)


class Payment(BaseModel):
    """Represents a Payment created in the PayPal portal"""

    class Options(enum.Enum):
        CERTIFIED = "CERTIFIED"
        SUPPORT = "SUPPORT"
        ADFREE = "ADFREE"

    draw = models.ForeignKey(
        BaseDraw, on_delete=models.CASCADE, related_name="_payments"
    )
    payed = models.BooleanField(default=False)
    draw_url = models.URLField()
    paypal_id = models.CharField(max_length=500, db_index=True)

    option_certified = models.BooleanField(default=False)
    option_support = models.BooleanField(default=False)
    option_adfree = models.BooleanField(default=False)

    def __repr__(self):
        options_str = ""
        options_str += "Y" if self.option_certified else "N"
        options_str += "Y" if self.option_support else "N"
        options_str += "Y" if self.option_adfree else "N"
        return "<%s  draw=%r, payed=%r, options=%r>" % (
            self.__class__.__name__,
            self.draw,
            self.payed,
            options_str,
        )

    def __str__(self):
        return repr(self)


class Tournament(BaseDraw, ParticipantsMixin):
    def generate_result(self):
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS)
        )
        random.shuffle(participants)
        groups = [list() for _ in range((len(participants) + 1) // 2)]
        for group, participant in zip(itertools.cycle(groups), participants):
            group.append(participant)
        return groups


DRAW_TYPES = [
    Coin,
    Groups,
    Letter,
    Link,
    Lottery,
    Raffle,
    RandomNumber,
    Spinner,
    Tournament,
]
