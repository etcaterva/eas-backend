from rest_framework import serializers

from . import models


class BaseSerializer(serializers.ModelSerializer):
    BASE_FIELDS = ('id', 'created_at', 'updated_at', 'title', 'description',
                   'results',)

    results = serializers.SerializerMethodField()

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

    def validate(self, data):
        if data["range_min"] > data["range_max"]:
            raise serializers.ValidationError('invalid_range')
        return data
