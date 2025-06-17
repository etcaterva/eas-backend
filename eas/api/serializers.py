import requests
from rest_framework import serializers

from . import instagram, models, tiktok

# pylint: disable=abstract-method


class StringListField(serializers.ListField):
    child = serializers.CharField(min_length=1, max_length=2000)


COMMON_FIELDS = (
    "id",
    "created_at",
)


class DrawTossPayloadSerializer(serializers.Serializer):
    schedule_date = serializers.DateTimeField(allow_null=True, required=False)


class DrawRetossPayloadSerializer(serializers.Serializer):
    prize_id = serializers.CharField(min_length=1)


class DrawMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientDrawMetaData
        fields = (
            "client",
            "key",
            "value",
        )


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = (
        *COMMON_FIELDS,
        "updated_at",
        "title",
        "description",
        "results",
        "metadata",
        "private_id",
        "payments",
    )

    results = serializers.SerializerMethodField()
    payments = serializers.SerializerMethodField()
    metadata = DrawMetadataSerializer(many=True, required=False)

    def create(self, validated_data):
        data_copy = dict(validated_data)
        metadata_list = data_copy.pop("metadata", [])
        draw = self.__class__.Meta.model.objects.create(  # pylint: disable=no-member
            **data_copy
        )
        metadata_instances = [
            models.ClientDrawMetaData(draw=draw, **metadata)
            for metadata in metadata_list
        ]
        models.ClientDrawMetaData.objects.bulk_create(metadata_instances)
        return draw

    @classmethod
    def get_results(cls, instance):
        return [
            ResultSerializer(result).data
            for result in models.Result.objects.filter(draw_id=instance.id).order_by(
                "-created_at"
            )
        ]

    @classmethod
    def get_payments(cls, instance):
        return instance.payments


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Result
        fields = (
            "created_at",
            "value",
            "schedule_date",
        )

    value = serializers.JSONField(allow_null=True)


class RandomNumberSerializer(BaseSerializer):
    class Meta:
        model = models.RandomNumber
        fields = BaseSerializer.BASE_FIELDS + (
            "range_min",
            "range_max",
            "number_of_results",
            "allow_repeated_results",
        )

    number_of_results = serializers.IntegerField(min_value=1, max_value=50)

    def validate(self, data):  # pylint: disable=arguments-differ
        num_values_in_range = data["range_max"] - data["range_min"] + 1

        if num_values_in_range < 1:
            raise serializers.ValidationError("invalid_range")
        if not data.get("allow_repeated_results", True) and (
            data.get("number_of_results", 1) > num_values_in_range
        ):
            raise serializers.ValidationError("invalid_range")
        return data


class LetterSerializer(BaseSerializer):
    class Meta:
        model = models.Letter
        fields = BaseSerializer.BASE_FIELDS + (
            "number_of_results",
            "allow_repeated_results",
        )

    number_of_results = serializers.IntegerField(min_value=1, max_value=2000)

    def validate(self, data):  # pylint: disable=arguments-differ
        if not data.get("allow_repeated_results", False) and (
            data.get("number_of_results", 1) > 26
        ):
            raise serializers.ValidationError("invalid_number_of_results")
        return data


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Prize
        fields = COMMON_FIELDS + (
            "name",
            "url",
        )


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Participant
        fields = COMMON_FIELDS + (
            "name",
            "facebook_id",
        )


class LinkSerializer(BaseSerializer):
    class Meta:
        model = models.Link
        fields = BaseSerializer.BASE_FIELDS + (
            "items_set1",
            "items_set2",
        )

    items_set1 = StringListField(min_length=1, max_length=2000)
    items_set2 = StringListField(min_length=1, max_length=2000)


class RaffleSerializer(BaseSerializer):
    class Meta:
        model = models.Raffle
        fields = BaseSerializer.BASE_FIELDS + (
            "prizes",
            "participants",
        )

    prizes = PrizeSerializer(many=True, required=True)
    participants = ParticipantSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        prizes = data.pop("prizes")
        if not prizes:
            raise serializers.ValidationError("Prizes cannot be empty")
        participants = data.pop("participants")
        draw = super().create(data)
        prize_instances = [models.Prize(draw=draw, **prize) for prize in prizes]
        models.Prize.objects.bulk_create(prize_instances)
        participant_instances = [
            models.Participant(draw=draw, **participant) for participant in participants
        ]
        models.Participant.objects.bulk_create(participant_instances)
        return draw


class LotterySerializer(BaseSerializer):
    class Meta:
        model = models.Lottery
        fields = BaseSerializer.BASE_FIELDS + ("participants", "number_of_results")

    participants = ParticipantSerializer(many=True, required=True)
    number_of_results = serializers.IntegerField(min_value=1, required=False)

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop("participants")
        draw = super().create(data)
        participant_instances = [
            models.Participant(draw=draw, **participant) for participant in participants
        ]
        models.Participant.objects.bulk_create(participant_instances)
        return draw


class GroupsSerializer(BaseSerializer):
    class Meta:
        model = models.Groups
        fields = BaseSerializer.BASE_FIELDS + (
            "number_of_groups",
            "participants",
        )

    participants = ParticipantSerializer(many=True, required=True)
    number_of_groups = serializers.IntegerField(min_value=2)

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop("participants")
        draw = super().create(data)
        participant_instances = [
            models.Participant(draw=draw, **participant) for participant in participants
        ]
        models.Participant.objects.bulk_create(participant_instances)
        return draw


class TournamentSerializer(BaseSerializer):
    class Meta:
        model = models.Tournament
        fields = BaseSerializer.BASE_FIELDS + ("participants",)

    participants = ParticipantSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop("participants")
        draw = super().create(data)
        participant_instances = [
            models.Participant(draw=draw, **participant) for participant in participants
        ]
        models.Participant.objects.bulk_create(participant_instances)
        return draw


class SpinnerSerializer(BaseSerializer):
    class Meta:
        model = models.Spinner
        fields = BaseSerializer.BASE_FIELDS


class CoinSerializer(BaseSerializer):
    class Meta:
        model = models.Coin
        fields = BaseSerializer.BASE_FIELDS


class SecretSantaParticipantSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField(max_length=100, required=False)
    phone_number = serializers.RegexField(
        regex=r"^\+\d{1,3}\d{4,14}$", max_length=100, required=False
    )
    exclusions = serializers.ListField(
        child=serializers.CharField(max_length=100), max_length=500, required=False
    )

    def validate(self, data):  # pylint: disable=arguments-differ
        if not data.get("email") and not data.get("phone_number"):
            raise serializers.ValidationError("phone_or_email_required")
        return data


class SecretSantaSerializer(serializers.Serializer):
    participants = serializers.ListField(
        child=SecretSantaParticipantSerializer(), min_length=1, max_length=100
    )
    language = serializers.ChoiceField(choices=["es", "en"])
    admin_email = serializers.EmailField(max_length=100, required=False)


class PayPalCreateSerialzier(serializers.Serializer):
    options = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[v.value for v in models.Payment.Options]
        ),
        min_length=1,
    )
    draw_id = serializers.CharField(max_length=100)
    draw_url = serializers.URLField()


class RevolutCreateSerialzier(serializers.Serializer):
    options = serializers.ListField(
        child=serializers.ChoiceField(
            choices=[v.value for v in models.Payment.Options]
        ),
        min_length=1,
    )
    draw_id = serializers.CharField(max_length=100)
    draw_url = serializers.URLField()


class PromoCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)
    draw_id = serializers.CharField(max_length=100)


class TiktokSerializer(BaseSerializer):
    class Meta:
        model = models.Tiktok
        fields = BaseSerializer.BASE_FIELDS + (
            "post_url",
            "min_mentions",
            "prizes",
        )

    prizes = PrizeSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        prizes = data.pop("prizes")
        if not prizes:
            raise serializers.ValidationError("Prizes cannot be empty")
        try:
            tiktok.get_comments(data["post_url"])
        except (requests.exceptions.ConnectionError, tiktok.NotFoundError):
            pass
        except tiktok.InvalidURL:
            raise serializers.ValidationError("Invalid post URL") from None
        draw = super().create(data)
        prize_instances = [models.Prize(draw=draw, **prize) for prize in prizes]
        models.Prize.objects.bulk_create(prize_instances)
        return draw


class InstagramSerializer(BaseSerializer):
    class Meta:
        model = models.Instagram
        fields = BaseSerializer.BASE_FIELDS + (
            "post_url",
            "use_likes",
            "min_mentions",
            "prizes",
        )

    prizes = PrizeSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        prizes = data.pop("prizes")
        if not prizes:
            raise serializers.ValidationError("Prizes cannot be empty")
        try:
            instagram.get_comments(data["post_url"])
        except (requests.exceptions.ConnectionError, instagram.NotFoundError):
            pass
        except instagram.InvalidURL:
            raise serializers.ValidationError("Invalid post URL") from None
        draw = super().create(data)
        prize_instances = [models.Prize(draw=draw, **prize) for prize in prizes]
        models.Prize.objects.bulk_create(prize_instances)
        return draw


class ShiftIntervalSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField(allow_null=False, required=True)
    end_time = serializers.DateTimeField(allow_null=False, required=True)


class ShiftsSerializer(BaseSerializer):
    class Meta:
        model = models.Shifts
        fields = BaseSerializer.BASE_FIELDS + (
            "intervals",
            "participants",
        )

    # participants = ParticipantSerializer(many=True, required=True)
    # intervals = ShiftIntervalSerializer(many=True, required=True)
    participants = serializers.ListField(
        child=ParticipantSerializer(), min_length=1, max_length=500
    )
    intervals = serializers.ListField(
        child=ShiftIntervalSerializer(), min_length=1, max_length=500
    )

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop("participants")
        intervals = data["intervals"]
        if len(intervals) < len(participants):
            raise serializers.ValidationError(
                "Not enough intervals, got {len(intervals)}, need {len(participants)}"
            )
        draw = super().create(data)
        participant_instances = [
            models.Participant(draw=draw, **participant) for participant in participants
        ]
        models.Participant.objects.bulk_create(participant_instances)
        return draw


class InstagramPreviewSerializer(serializers.Serializer):
    url = serializers.URLField()
