import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import models, serializers

LOG = logging.getLogger(__name__)


class BaseDrawViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):

    MODEL = None  # To be set by concrete implementations
    PRIVATE_FIELDS = ["private_id"]  # Fields to show only to the owner

    @classmethod
    def remove_private_fields(cls, data):
        for attr in cls.PRIVATE_FIELDS:
            data.pop(attr)

    def create(self, request, *args, **kwargs):
        LOG.info("Creating new draw for request: %s", request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draw = serializer.save()
        headers = self.get_success_headers(serializer.data)
        LOG.info("Created draw %s", draw)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def _get_draw(self, pk):
        try:
            return get_object_or_404(self.MODEL, id=pk)
        except Http404:
            return get_object_or_404(self.MODEL, private_id=pk)

    def retrieve(
        self, request, *args, pk=None, **kwargs
    ):  # pylint: disable=unused-argument
        LOG.info("Retrieving draw by id: %s", pk)
        instance = self._get_draw(pk)
        try:
            self._ready_to_toss_check(instance)
        except ValidationError:
            pass
        else:
            instance.resolve_scheduled_results()
        serializer = self.get_serializer(instance)
        result_data = serializer.data
        if pk != result_data["private_id"]:
            self.remove_private_fields(result_data)
        LOG.info("Returning draw %s", instance)
        return Response(result_data)

    @action(methods=["post"], detail=True)
    def toss(self, request, pk):
        LOG.info("Tossing draw with id: %s", pk)
        draw = get_object_or_404(self.MODEL, private_id=pk)
        serializer = serializers.DrawTossPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule_date = serializer.validated_data.get("schedule_date")
        if schedule_date:
            result = draw.schedule_toss(schedule_date)
        else:
            self._ready_to_toss_check(draw)
            result = draw.toss()
        result_serializer = serializers.ResultSerializer(result)
        LOG.info("Generated result: %s", result)
        return Response(result_serializer.data)

    def _ready_to_toss_check(self, _):  # pylint: disable=no-self-use
        pass


class RandomNumberViewSet(BaseDrawViewSet):
    MODEL = models.RandomNumber
    serializer_class = serializers.RandomNumberSerializer

    queryset = MODEL.objects.all()


class ParticipantsMixin:
    """Adds the participant related endpoints"""

    @action(methods=["post"], detail=True)
    def participants(self, request, pk):
        LOG.info("Adding participant to draw %s", pk)
        draw = self._get_draw(pk)
        serializer = serializers.ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(draw=draw)
        LOG.info("Participant %s added", request.data)

        # Check for duplicated participants
        draw = self._get_draw(pk)
        facebook_participants_id = set()
        for participant in draw.participants.all():
            facebook_id = participant.facebook_id
            if facebook_id is None:
                pass
            elif facebook_id in facebook_participants_id:
                participant.delete()
            else:
                facebook_participants_id.add(facebook_id)
        return Response({}, status.HTTP_201_CREATED)


class RaffleViewSet(BaseDrawViewSet, ParticipantsMixin):
    MODEL = models.Raffle
    serializer_class = serializers.RaffleSerializer

    queryset = MODEL.objects.all()

    def _ready_to_toss_check(self, draw):  # pylint: disable=no-self-use
        if not draw.participants.count():
            raise ValidationError(
                f"The draw needs to have at least {draw.prizes.count()}"
                " participants."
            )


class LotteryViewSet(BaseDrawViewSet, ParticipantsMixin):
    MODEL = models.Lottery
    serializer_class = serializers.LotterySerializer

    queryset = MODEL.objects.all()

    def _ready_to_toss_check(self, draw):  # pylint: disable=no-self-use
        if draw.participants.count() < draw.number_of_results:
            raise ValidationError(
                f"The draw needs to have at least {draw.number_of_results}"
                " participants."
            )


class GroupsViewSet(BaseDrawViewSet, ParticipantsMixin):
    MODEL = models.Groups
    serializer_class = serializers.GroupsSerializer

    queryset = MODEL.objects.all()

    def _ready_to_toss_check(self, draw):  # pylint: disable=no-self-use
        if draw.participants.count() < draw.number_of_groups:
            raise ValidationError(
                f"The draw needs to have at least {draw.number_of_groups}"
                " participants."
            )


class SpinnerViewSet(BaseDrawViewSet):
    MODEL = models.Spinner
    serializer_class = serializers.SpinnerSerializer

    queryset = MODEL.objects.all()


class LetterViewSet(BaseDrawViewSet):
    MODEL = models.Letter
    serializer_class = serializers.LetterSerializer

    queryset = MODEL.objects.all()


class CoinViewSet(BaseDrawViewSet):
    MODEL = models.Coin
    serializer_class = serializers.CoinSerializer

    queryset = MODEL.objects.all()


class LinkViewSet(BaseDrawViewSet):
    MODEL = models.Link
    serializer_class = serializers.LinkSerializer

    queryset = MODEL.objects.all()
