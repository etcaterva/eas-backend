from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from . import models, serializers


class GenericDrawViewSet(mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    pass


class RandomNumber(GenericDrawViewSet):
    MODEL = models.RandomNumber
    SERIALIZER = serializers.RandomNumberSerializer
    RESULT_SERIALIZER = serializers.RandomNumberResultSerializer

    queryset = MODEL.objects.all()
    serializer_class = SERIALIZER

    def create(self, request, *args, **kwargs):
        result = super().create(request, *args, **kwargs)
        draw = self.MODEL.objects.get(id=result.data["id"])
        result.data["private_id"] = draw.private_id
        return result

    @action(methods=['post'], detail=True)
    def toss(self, _, pk):
        draw = get_object_or_404(self.MODEL, private_id=pk)
        result = draw.toss()
        result_serializer = self.RESULT_SERIALIZER(result)
        return Response(result_serializer.data)
