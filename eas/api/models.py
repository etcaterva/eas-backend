"""Models of the objects used in EAS"""
import contextlib
import datetime as dt
import enum
import itertools
import random
import string
import uuid

from django.db import models
from jsonfield import JSONField

from . import instagram, tiktok


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


class PayableMixin:
    """If you have a _payments field from a Payment model, enables to return standard payment options"""

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


class BaseDraw(BaseModel, PayableMixin):
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

    def has_unresolved_results(self):
        """Checks if there is any result pending resolution"""
        for result in self.results.filter(
            schedule_date__lte=dt.datetime.now(dt.timezone.utc)
        ):
            if result.value is None:
                return True
        return False

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
    range_max = models.BigIntegerField()

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


class SecretSanta(BaseModel, PayableMixin):
    """Links the different results generated from a secret santa toss"""


class SecretSantaResult(BaseModel):
    draw = models.ForeignKey(
        SecretSanta,
        on_delete=models.CASCADE,
        null=True,
        unique=False,
    )
    source = models.CharField(max_length=100)
    target = models.CharField(max_length=100)
    revealed = models.BooleanField(default=False)
    valid = models.BooleanField(default=True)

    def __repr__(self):
        return "<%s  (%r,%r)>" % (self.__class__.__name__, self.source, self.target)

    def __str__(self):
        return repr(self)


class Payment(BaseModel):
    """Represents a Payment for a draw

    Can be created via PayPal or a discount code.
    """

    class Options(enum.Enum):
        CERTIFIED = "CERTIFIED"
        SUPPORT = "SUPPORT"
        ADFREE = "ADFREE"

    draw = models.ForeignKey(
        BaseDraw,
        on_delete=models.CASCADE,
        related_name="_payments",
        null=True,
        blank=True,
    )
    secret_santa = models.ForeignKey(
        SecretSanta,
        on_delete=models.CASCADE,
        related_name="_payments",
        null=True,
        blank=True,
    )

    payed = models.BooleanField(default=False)
    draw_url = models.URLField(null=True)
    paypal_id = models.CharField(max_length=500, db_index=True, null=True)

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
        counter = itertools.count()
        result = []

        match_count = 2 ** (len(participants) - 1).bit_length()  # closest power of 2
        matches = []
        while match_count > 1:
            match_count //= 2
            next_matches = [
                {
                    "id": next(counter),
                    "participants": [],
                    "score": None,
                    "winner_id": None,
                    "next_match_id": None,
                }
                for _ in range(match_count)
            ]
            next_match_ids = itertools.chain(
                *zip(
                    [m["id"] for m in next_matches],
                    [m["id"] for m in next_matches],
                )
            )
            for m in matches:
                m["next_match_id"] = next(next_match_ids)
            matches = next_matches
            result += matches

        round1_count = 2 ** (len(participants) - 1).bit_length()  # closest power of 2
        participants_iter = iter(participants)
        round1_count //= 2
        with contextlib.suppress(StopIteration):
            for i in range(round1_count):
                result[i]["participants"].append(next(participants_iter))
            for i in range(round1_count):
                result[i]["participants"].append(next(participants_iter))
        for i in range(round1_count):  # Resolve orphan matches
            match = result[i]
            assert match["participants"] is not None
            if len(match["participants"]) > 1:  # Standard match
                continue
            assert match["next_match_id"] is not None
            match["winner_id"] = match["participants"][0]["id"]
            next_match = result[match["next_match_id"]]
            assert next_match["id"] == match["next_match_id"]
            next_match["participants"].append(match["participants"][0])
            assert len(next_match["participants"]) <= 2

        return result


class Instagram(BaseDraw, PrizesMixin):
    post_url = models.URLField()
    use_likes = models.BooleanField(default=False)
    min_mentions = models.IntegerField(default=0)

    def fetch_comments(self):
        comments = {
            c.username: {
                "username": c.username,
                "userpic": c.userpic,
                "text": c.text,
                "id": c.id,
            }
            for c in instagram.get_comments(
                self.post_url, self.min_mentions, require_like=self.use_likes
            )
        }  # dedup participants
        comments = list(comments.values())
        random.shuffle(comments)
        return comments

    def generate_result(self):
        comments = self.fetch_comments()
        result = []
        for prize, winner in zip(
            self.prizes.values(*PrizesMixin.SERIALIZE_FIELDS),
            itertools.cycle(comments),
        ):
            result.append({"prize": prize, "comment": winner})
        return result


class Tiktok(BaseDraw, PrizesMixin):
    post_url = models.URLField()
    min_mentions = models.IntegerField(default=0)

    def fetch_comments(self):
        comments = {
            c.username: {
                "text": c.text,
                "id": c.id,
                "url": c.url,
                "username": c.username,
                "userid": c.userid,
                "userpic": c.userpic,
            }
            for c in tiktok.get_comments(self.post_url, self.min_mentions)
        }  # dedup participants
        comments = list(comments.values())
        random.shuffle(comments)
        return comments

    def generate_result(self):
        comments = self.fetch_comments()
        result = []
        for prize, winner in zip(
            self.prizes.values(*PrizesMixin.SERIALIZE_FIELDS),
            itertools.cycle(comments),
        ):
            result.append({"prize": prize, "comment": winner})
        return result


class Shifts(BaseDraw, ParticipantsMixin):
    intervals = JSONField()

    def generate_result(self):
        intervals = list(self.intervals)
        participants = list(
            self.participants.values(*ParticipantsMixin.SERIALIZE_FIELDS)
        )
        random.shuffle(participants)
        return [
            {"interval": interval, "participants": [participant]}
            for interval, participant in zip(intervals, participants)
        ]


def compute_checksum(code):
    acc = 0
    for l in code:
        acc += ord(l)
    return chr(ord("A") + (acc % 25))


def created_discount_code():
    code = "".join([random.choice(string.ascii_uppercase) for _ in range(7)])
    return code + compute_checksum(code)


class PromoCode(BaseModel):
    """Codes to get free certified draws"""

    code = models.CharField(
        max_length=8,
        default=created_discount_code,
        unique=True,
        null=False,
        editable=False,
    )

    def __repr__(self):
        return "<%s(%r) %r)>" % (self.__class__.__name__, self.id, self.code)

    def __str__(self):
        return repr(self)


DRAW_TYPES = [
    Coin,
    Groups,
    Instagram,
    Letter,
    Link,
    Lottery,
    Raffle,
    RandomNumber,
    Shifts,
    Spinner,
    Tiktok,
    Tournament,
]
