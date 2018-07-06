from rest_framework import serializers

from . import models


class DrawMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientDrawMetaData
        fields = ('client', 'key', 'value',)


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = ('id', 'created_at', 'updated_at', 'title', 'description',
                   'results', 'metadata',)

    results = serializers.SerializerMethodField()
    metadata = DrawMetadataSerializer(many=True, default=[])

    def create(self, validated_data):
        data_copy = dict(validated_data)
        metadata_list = data_copy.pop('metadata')
        draw = self.__class__.Meta.model.objects.create(**data_copy) # pylint: disable=no-member
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
