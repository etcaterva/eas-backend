from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from drf_yasg.utils import swagger_auto_schema

from . import models, serializers


class BaseDrawViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):

    PRIVATE_FIELDS = ['private_id']  # Fields to show only to the owner

    @classmethod
    def remove_private_fields(cls, data):
        for attr in cls.PRIVATE_FIELDS:
            data.pop(attr)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            instance = get_object_or_404(self.MODEL,
                                         private_id=self.kwargs['pk'])
        serializer = self.get_serializer(instance)
        result_data = serializer.data
        if kwargs["pk"] != result_data["private_id"]:
            self.remove_private_fields(result_data)
        return Response(result_data)

    @swagger_auto_schema(methods=['post'],
                         request_body=serializers.DrawTossPayloadSerializer)
    @action(methods=['post'], detail=True)
    def toss(self, _, pk):
        draw = get_object_or_404(self.MODEL, private_id=pk)
        result = self._toss_draw(draw)
        result_serializer = serializers.ResultSerializer(result)
        return Response(result_serializer.data)

    def _toss_draw(self, draw):  # pylint: disable=no-self-use
        return draw.toss()


class RandomNumberViewSet(BaseDrawViewSet):
    MODEL = models.RandomNumber
    serializer_class = serializers.RandomNumberSerializer

    queryset = MODEL.objects.all()


class RaffleViewSet(BaseDrawViewSet):
    MODEL = models.Raffle
    serializer_class = serializers.RaffleSerializer

    queryset = MODEL.objects.all()

    def _toss_draw(self, draw):
        if draw.participants.count() < draw.prizes.count():
            raise ValidationError(
                f"The draw needs to have at least {draw.participants.count()}"
                " participants.")
        return draw.toss()
