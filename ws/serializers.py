from rest_framework import serializers

from . import models


class RandomNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RandomNumber
        fields = ('id', 'created_at', 'updated_at', 'title', 'description',
                  'range_min', 'range_max', 'results',)

    RESULT_CLASS = models.RandomNumberResult

    results = serializers.SerializerMethodField()

    @classmethod
    def get_results(cls, instance):
        return [
            RandomNumberResultSerializer(result).data
            for result in cls.RESULT_CLASS.objects
                .filter(draw_id=instance.id)
                .order_by("-created_at")
        ]


class RandomNumberResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RandomNumberResult
        fields = ('created_at', 'value',)
