from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from . import models, serializers


class BaseDrawViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    @classmethod
    def enrich_for_owner(cls, data, draw):
        return {
            **data,
            "private_id": draw.private_id,
        }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draw = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(self.enrich_for_owner(serializer.data, draw),
                        status=status.HTTP_201_CREATED, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        is_owner = False  # Horrible flag to know if the user is the owner
        try:
            instance = self.get_object()
        except Http404:
            instance = get_object_or_404(self.MODEL,
                                         private_id=self.kwargs['pk'])
            is_owner = True
        serializer = self.get_serializer(instance)
        result_data = serializer.data
        if is_owner:
            result_data = self.enrich_for_owner(result_data, instance)
        return Response(result_data)

    @action(methods=['post'], detail=True)
    def toss(self, _, pk):
        draw = get_object_or_404(self.MODEL, private_id=pk)
        result = draw.toss()
        result_serializer = serializers.ResultSerializer(result)
        return Response(result_serializer.data)


class RandomNumberViewSet(BaseDrawViewSet):
    MODEL = models.RandomNumber
    serializer_class = serializers.RandomNumberSerializer

    queryset = MODEL.objects.all()
