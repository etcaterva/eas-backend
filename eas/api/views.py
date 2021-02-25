import logging
import random

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls.base import reverse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import email, models, paypal, serializers

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
    ):  # pylint: disable=unused-argument, arguments-differ
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


class TournamentViewSet(BaseDrawViewSet, ParticipantsMixin):
    MODEL = models.Tournament
    serializer_class = serializers.TournamentSerializer
    queryset = MODEL.objects.all()


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


def _ss_find_target(targets, exclusions):
    potential_targets = set(targets) - exclusions
    if not potential_targets:
        return
    return random.choice(list(potential_targets))


def _ss_build_results(participants, exclusions_map):
    results = []
    targets = list(participants)
    for source in participants:
        target = _ss_find_target(targets, exclusions_map[source])
        if not target:
            return
        targets.remove(target)
        results.append((source, target))
    return results


class SecretSantaSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    def create(self, request, *args, **kwargs):
        LOG.info("Creating new secret santa")
        serializer = serializers.SecretSantaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        emails_map = {p["name"]: p["email"] for p in data["participants"]}
        exclusions_map = {
            p["name"]: set(p.get("exclusions") or []) for p in data["participants"]
        }
        LOG.info("Using exclusion map: %r", exclusions_map)
        for participant, exclusions in exclusions_map.items():
            exclusions.add(participant)
        participants = {p["name"] for p in data["participants"]}
        for _ in range(min(50, len(participants))):
            results = _ss_build_results(participants, exclusions_map)
            if results is not None:
                break
        else:
            raise ValidationError("Unable to match participants")
        for source, target in results:
            result = models.SecretSantaResult(source=source, target=target)
            result.save()
            target = emails_map[source]
            try:
                email.send_secret_santa_mail(target, result.id, data["language"])
            except Exception:  # pragma: no cover  # pylint: disable=broad-except
                LOG.exception("Failed to send email to %s", target)
        LOG.info("Created secret santa results %s", results)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def retrieve(
        self, request, *args, pk=None, **kwargs
    ):  # pylint: disable=unused-argument, arguments-differ
        LOG.info("Retrieving secret santa result by id: %s", pk)
        result = get_object_or_404(models.SecretSantaResult, id=pk)
        LOG.info("Returning result %s", result)
        return Response({"source": result.source, "target": result.target})


@api_view(["POST"])
def paypal_create(request):
    payment_options = models.Payment.Options
    LOG.info("Initiating paypal payment for request: %s", request.data)
    serializer = serializers.PayPalCreateSerialzier(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    options = data["options"]
    ammount = 0
    if payment_options.CERTIFIED.value in options:
        ammount += 1
    if payment_options.SUPPORT.value in options:
        ammount += 2
    if payment_options.ADFREE.value in options:
        ammount += 2
    paypal_id, paypal_url = paypal.create_payment(
        draw_url=data["draw_url"],
        accept_url=request.build_absolute_uri(reverse("paypal-accept")),
        ammount=ammount,
    )
    payment = models.Payment(
        draw_id=data["draw_id"],
        draw_url=data["draw_url"],
        paypal_id=paypal_id,
        option_certified=payment_options.CERTIFIED.value in options,
        option_support=payment_options.SUPPORT.value in options,
        option_adfree=payment_options.ADFREE.value in options,
    )
    payment.save()
    LOG.info("Paypal payment creation succeeded: %s", payment)
    return Response({"redirect_url": paypal_url})


@api_view(["GET"])
def paypal_accept(request):
    print(request.GET)
    payment_id = request.GET["paymentId"]
    payer_id = request.GET["PayerID"]
    LOG.info("Accepting payment for id %r and payer %r", payment_id, payer_id)
    payment = get_object_or_404(models.Payment, paypal_id=payment_id)
    payment.payed = True
    payment.save()
    paypal.accept_payment(payment_id, payer_id)
    LOG.info("Payment %r accepted", payment)
    return redirect(payment.draw_url)
