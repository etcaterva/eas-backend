from rest_framework import serializers

from . import models

# pylint: disable=abstract-method


COMMON_FIELDS = ('id', 'created_at',)


class DrawTossPayloadSerializer(serializers.Serializer):
    schedule_date = serializers.DateTimeField(allow_null=True, required=False)


class DrawMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientDrawMetaData
        fields = ('client', 'key', 'value',)


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = (*COMMON_FIELDS, 'updated_at', 'title', 'description',
                   'results', 'metadata', 'private_id')

    results = serializers.SerializerMethodField()
    metadata = DrawMetadataSerializer(many=True, required=False)

    def create(self, validated_data):
        data_copy = dict(validated_data)
        metadata_list = data_copy.pop('metadata', [])
        draw = self.__class__.Meta.model.objects.create(**data_copy)  # pylint: disable=no-member
        for metadata in metadata_list:
            models.ClientDrawMetaData.objects.create(draw=draw, **metadata)
        return draw

    @classmethod
    def get_results(cls, instance):
        return [
            ResultSerializer(result).data
            for result in models.Result.objects
            .filter(draw_id=instance.id)
            .order_by("-created_at")
        ]


class ResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Result
        fields = ('created_at', 'value', 'schedule_date',)

    value = serializers.JSONField(allow_null=True)


class RandomNumberSerializer(BaseSerializer):
    class Meta:
        model = models.RandomNumber
        fields = BaseSerializer.BASE_FIELDS + (
            'range_min', 'range_max', 'number_of_results',
            'allow_repeated_results',
        )

    number_of_results = serializers.IntegerField(min_value=1, max_value=50)

    def validate(self, data):  # pylint: disable=arguments-differ
        num_values_in_range = data["range_max"] - data["range_min"]
        if num_values_in_range < 1:
            raise serializers.ValidationError('invalid_range')
        if not data["allow_repeated_results"] and (
                data["number_of_results"] > num_values_in_range):
            raise serializers.ValidationError('invalid_range')
        return data


class PrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Prize
        fields = COMMON_FIELDS + ('name', 'url', )


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Participant
        fields = COMMON_FIELDS + ('name', 'facebook_id', )


class RaffleSerializer(BaseSerializer):
    class Meta:
        model = models.Raffle
        fields = BaseSerializer.BASE_FIELDS + ('prizes', 'participants',)

    prizes = PrizeSerializer(many=True, required=True)
    participants = ParticipantSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        prizes = data.pop('prizes')
        if not prizes:
            raise serializers.ValidationError("Prizes cannot be empty")
        participants = data.pop('participants')
        draw = super().create(data)
        for prize in prizes:
            models.Prize.objects.create(draw=draw, **prize)
        for participant in participants:
            models.Participant.objects.create(draw=draw, **participant)
        return draw


class LotterySerializer(BaseSerializer):
    class Meta:
        model = models.Lottery
        fields = BaseSerializer.BASE_FIELDS + ('participants',)

    participants = ParticipantSerializer(many=True, required=True)

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop('participants')
        draw = super().create(data)
        for participant in participants:
            models.Participant.objects.create(draw=draw, **participant)
        return draw


class GroupsSerializer(BaseSerializer):
    class Meta:
        model = models.Groups
        fields = BaseSerializer.BASE_FIELDS + ('number_of_groups',
                                               'participants',)

    participants = ParticipantSerializer(many=True, required=True)
    number_of_groups = serializers.IntegerField(min_value=2)

    def create(self, validated_data):
        data = dict(validated_data)
        participants = data.pop('participants')
        draw = super().create(data)
        for participant in participants:
            models.Participant.objects.create(draw=draw, **participant)
        return draw


class SpinnerSerializer(BaseSerializer):
    class Meta:
        model = models.Spinner
        fields = BaseSerializer.BASE_FIELDS
