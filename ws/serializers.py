from rest_framework import serializers

from . import models


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = ('id', 'created_at', 'updated_at', 'title', 'description',
                   'results',)

    results = serializers.SerializerMethodField()

    @classmethod
    def get_results(cls, instance):
        return [
            cls.RESULT_SERIALIZER(result).data
            for result in cls.RESULT_MODEL.objects
                .filter(draw_id=instance.id)
                .order_by("-created_at")
        ]


class RandomNumberResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RandomNumberResult
        fields = ('created_at', 'value',)


class RandomNumberSerializer(BaseSerializer):
    class Meta:
        model = models.RandomNumber
        fields = BaseSerializer.BASE_FIELDS + ('range_min', 'range_max',)

    RESULT_MODEL = models.RandomNumberResult
    RESULT_SERIALIZER = RandomNumberResultSerializer
