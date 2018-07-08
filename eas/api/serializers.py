from rest_framework import serializers

from . import models

# pylint: disable=abstract-method


COMMON_FIELDS = ('id', 'created_at',)


class DrawTossPayloadSerializer(serializers.Serializer):
    pass


class DrawMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientDrawMetaData
        fields = ('client', 'key', 'value',)


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = (*COMMON_FIELDS, 'updated_at', 'title', 'description',
                   'results', 'metadata',)

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
        fields = ('created_at', 'value',)

    value = serializers.JSONField()


class RandomNumberSerializer(BaseSerializer):
    class Meta:
        model = models.RandomNumber
        fields = BaseSerializer.BASE_FIELDS + ('range_min', 'range_max',)

    def validate(self, data):  # pylint: disable=arguments-differ
        if data["range_min"] > data["range_max"]:
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
