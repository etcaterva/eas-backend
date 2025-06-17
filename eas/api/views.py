import datetime as dt
import logging

import requests.exceptions
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls.base import reverse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from . import (
    amazonsqs,
    instagram,
    models,
    paypal,
    revolut,
    secret_santa,
    serializers,
    tiktok,
)

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

    def _toss_unresolved_results(self, instance):
        if not instance.has_unresolved_results():
            return
        try:
            self._ready_to_toss_check(instance)
        except ValidationError:
            pass
        else:
            instance.resolve_scheduled_results()

    def retrieve(
        self, request, *args, pk=None, **kwargs
    ):  # pylint: disable=unused-argument, arguments-differ
        LOG.info("Retrieving draw by id: %s", pk)
        instance = self._get_draw(pk)
        self._toss_unresolved_results(instance)
        serializer = self.get_serializer(instance)
        result_data = serializer.data
        if pk != result_data["private_id"]:
            self.remove_private_fields(result_data)
        LOG.info("Returning draw with id: %s", pk)
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
        LOG.info("Generated result %s", result_serializer.data)
        draw.save()  # Updates updated_at
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
        draw.save()  # Updates updated_at
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


class SecretSantaSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    def create(self, request, *args, **kwargs):
        LOG.info("Creating new secret santa")
        serializer = serializers.SecretSantaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exclusions = []
        participants = []
        phones_map = {}
        emails_map = {}
        for p in data["participants"]:
            participant = p["name"]
            participants.append(participant)
            if p.get("phone_number"):
                phones_map[participant] = p["phone_number"]
            if p.get("email"):
                emails_map[participant] = p["email"]
            for e in p.get("exclusions", []):
                exclusions.append((participant, e))
        results = secret_santa.resolve_secret_santa(participants, exclusions)
        if not results:
            raise ValidationError("Unable to match participants")
        draw = models.SecretSanta()
        draw.save()
        emails = []
        phones = []
        for source, target in results:
            result = models.SecretSantaResult(source=source, target=target, draw=draw)
            result.save()
            if source in emails_map:
                target = emails_map[source]
                emails.append((target, result.id))
            else:
                target = phones_map[source]
                phones.append((target, result.id))
        amazonsqs.send_secret_santa_message(
            {
                "lang": data["language"],
                "mails": emails,
                "phones": phones,
                "draw_id": draw.id,
                "admin_email": data.get("admin_email"),
            }
        )
        LOG.info("Created secret santa results %s", results)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"id": draw.id}, status=status.HTTP_201_CREATED, headers=headers
        )

    def retrieve(
        self, request, *args, pk=None, **kwargs
    ):  # pylint: disable=unused-argument, arguments-differ
        LOG.info("Retrieving secret santa result by id: %s", pk)
        result = get_object_or_404(models.SecretSantaResult, id=pk)
        if not result.valid:
            raise ValidationError(
                f"Result {result.id} has been sent a invalidated by an admin",
                code="invalid",
            )
        result.revealed = True
        result.save()
        LOG.info("Returning result %s", result)
        return Response({"source": result.source, "target": result.target})


@api_view(["GET"])
def secret_santa_admin(request, pk):
    LOG.info("Retrieving secret santa draw by id: %s", pk)
    draw = get_object_or_404(models.SecretSanta, id=pk)
    result = {
        "id": draw.id,
        "created_at": draw.created_at,
        "participants": [],
        "payments": [str(p) for p in draw.payments],
    }
    for participant in models.SecretSantaResult.objects.filter(draw=draw).all():
        result["participants"].append(
            {
                "id": participant.id,
                "name": participant.source,
                "revealed": participant.revealed,
            }
        )
    LOG.info("Returning result %s", result)
    return Response(result)


@api_view(["POST"])
def secret_santa_resend_email(request, draw_pk, result_pk):
    LOG.info("Resending secret santa %s result %s", draw_pk, result_pk)
    draw = get_object_or_404(models.SecretSanta, id=draw_pk)
    result = get_object_or_404(models.SecretSantaResult, id=result_pk)
    if (not result.draw) or (result.draw.id != draw.id):
        raise ValidationError(f"Result {result.id} does not belong to {draw.id}")
    if result.revealed:
        raise ValidationError(
            f"Result {result.id} has been already revealed", code="revealed"
        )
    if (cutoff := result.created_at + dt.timedelta(hours=1)) > dt.datetime.now(
        dt.timezone.utc
    ):
        return Response(
            {
                "general": [
                    {
                        "id": result.id,
                        "message": "Result cannot be resent before cutoff",
                        "cutoff": cutoff,
                        "code": "too-early",
                    }
                ]
            },
            status=400,
        )

    # copy result:
    new_result = get_object_or_404(models.SecretSantaResult, id=result_pk)
    new_result.id = None
    new_result.created_at = None
    new_result.save()

    # Invalidate previous:
    result.valid = False
    result.draw = None
    result.save()

    payload = {
        "lang": request.data["language"],
    }
    if "email" in request.data:
        payload["mails"] = [(request.data["email"], new_result.id)]
    elif "phone_number" in request.data:
        payload["phones"] = [(request.data["phone_number"], new_result.id)]
    else:
        raise ValidationError("email or phone_number missing") from None
    amazonsqs.send_secret_santa_message(payload)
    LOG.info("Returning result %s", new_result)
    return Response({"new_result": new_result.id})


payment_options = models.Payment.Options


def calculate_payment(options):
    ammount = 0
    if payment_options.CERTIFIED.value in options:
        ammount += 1
    if payment_options.ADFREE.value in options:
        ammount += 1
    if payment_options.SUPPORT.value in options:
        ammount += 5
    assert ammount != 0
    ammount -= 0.01
    return ammount


@api_view(["POST"])
def paypal_create(request):
    LOG.info("Initiating paypal payment for request: %s", request.data)
    serializer = serializers.PayPalCreateSerialzier(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    options = data["options"]
    ammount = calculate_payment(options)
    paypal_id, paypal_url = paypal.create_payment(
        draw_url=data["draw_url"],
        accept_url=request.build_absolute_uri(reverse("paypal-accept")),
        amount=ammount,
    )
    payment = models.Payment(
        draw_url=data["draw_url"],
        paypal_id=paypal_id,
        option_certified=payment_options.CERTIFIED.value in options,
        option_support=payment_options.SUPPORT.value in options,
        option_adfree=payment_options.ADFREE.value in options,
    )
    if models.SecretSanta.objects.filter(pk=data["draw_id"]).exists():
        payment.secret_santa_id = data["draw_id"]
    else:
        payment.draw_id = data["draw_id"]
    payment.save()
    LOG.info("Paypal payment creation succeeded: %s", payment)
    return Response({"redirect_url": paypal_url})


@api_view(["GET"])
def paypal_accept(request):
    payment_id = request.GET["token"]
    payer_id = request.GET["PayerID"]
    LOG.info("Accepting payment for id %r and payer %r", payment_id, payer_id)
    payment = get_object_or_404(models.Payment, paypal_id=payment_id)
    if paypal.accept_payment(payment_id, payer_id):
        payment.payed = True
        payment.save()
        LOG.info("Payment %r accepted", payment)
    return redirect(payment.draw_url)


@api_view(["POST"])
def revolut_create(request):
    LOG.info("Initiating revolut payment for request: %s", request.data)
    serializer = serializers.RevolutCreateSerialzier(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    options = data["options"]
    ammount = calculate_payment(options)
    return_url = request.build_absolute_uri(
        reverse("revolut-accept", kwargs={"draw_id": data["draw_id"]})
    )
    payment_id, payment_url = revolut.create_payment(
        draw_url=data["draw_url"],
        accept_url=return_url,
        amount=ammount,
    )
    payment = models.Payment(
        draw_url=data["draw_url"],
        revolut_id=payment_id,
        option_certified=payment_options.CERTIFIED.value in options,
        option_support=payment_options.SUPPORT.value in options,
        option_adfree=payment_options.ADFREE.value in options,
    )
    if models.SecretSanta.objects.filter(pk=data["draw_id"]).exists():
        payment.secret_santa_id = data["draw_id"]
    else:
        payment.draw_id = data["draw_id"]
    payment.save()
    LOG.info("Payment creation succeeded: %s", payment)
    return Response({"redirect_url": payment_url})


@api_view(["GET"])
def revolut_accept(_, draw_id):
    try:
        payment = get_object_or_404(models.Payment, secret_santa_id=draw_id)
    except Http404:
        payment = get_object_or_404(models.Payment, draw_id=draw_id)
    LOG.info("Accepting payment for id %r", payment.revolut_id)
    if revolut.accept_payment(payment.revolut_id):
        payment.payed = True
        payment.save()
        LOG.info("Payment %r accepted", payment)
    return redirect(payment.draw_url)


class SocialNetworkCommentRaffleMixin:
    """Mixin for raffles on social network that use comments for the draw"""

    def _ready_to_toss_check(self, draw):  # pylint: disable=no-self-use
        # Check if a result is possible
        try:
            draw.generate_result()
        except (tiktok.InvalidURL, instagram.InvalidURL):
            LOG.info("Invalid draw %s, cannot toss", draw.private_id, exc_info=True)
            raise ValidationError(f"Invalid post URL: {draw.post_url}") from None
        except (tiktok.NotFoundError, instagram.NotFoundError):
            LOG.info("Draw %s has no comments", draw.private_id, exc_info=True)
            raise ValidationError("The post has no comments") from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            LOG.error("Timed out tossing draw %s", draw.private_id, exc_info=True)
            raise APIException("Timed-out tossing. Try again later.") from None

    @action(methods=["PATCH"], detail=True)
    def retoss(self, request, pk):
        LOG.info("Retossing draw with id: %s", pk)
        draw = get_object_or_404(self.MODEL, private_id=pk)
        serializer = serializers.DrawRetossPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prize_id = serializer.validated_data.get("prize_id")

        result = draw.results.order_by("created_at").last()
        if result is None:
            raise ValidationError(f"{draw} does not have any result")
        self._ready_to_toss_check(draw)

        result.id = None
        result.created_at = None
        new_comments = draw.fetch_comments()

        referenced_result_item = None
        for result_content in result.value:
            if result_content["prize"]["id"] == prize_id:
                referenced_result_item = result_content
        if referenced_result_item is None:
            raise ValidationError(
                f"{draw} does not have a result with prize {prize_id}"
            )

        for new_comment in new_comments:  # attempt finding a new comment
            if new_comment != referenced_result_item["comment"]:
                LOG.info("Replacing %s by %s", referenced_result_item, new_comment)
                referenced_result_item["comment"] = new_comment
                break

        result.save()

        result_serializer = serializers.ResultSerializer(result)
        LOG.info("Regenerated result %s", result_serializer.data)
        draw.save()  # Updates updated_at
        return Response(result_serializer.data)


class TiktokViewSet(SocialNetworkCommentRaffleMixin, BaseDrawViewSet):
    MODEL = models.Tiktok
    serializer_class = serializers.TiktokSerializer

    queryset = MODEL.objects.all()


class InstagramViewSet(SocialNetworkCommentRaffleMixin, BaseDrawViewSet):
    MODEL = models.Instagram
    serializer_class = serializers.InstagramSerializer

    queryset = MODEL.objects.all()


class ShiftsViewSet(BaseDrawViewSet):
    MODEL = models.Shifts
    serializer_class = serializers.ShiftsSerializer

    queryset = MODEL.objects.all()


@api_view(["POST"])
def redeem_promo_code(request):
    LOG.info("Redeeming promo code: %s", request.data)
    serializer = serializers.PromoCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    draw_id = data["draw_id"]
    get_object_or_404(models.BaseDraw, id=draw_id)
    code = data["code"]
    code_object = get_object_or_404(models.PromoCode, code=code)
    payment = models.Payment(
        draw_id=draw_id,
        payed=True,
        option_certified=True,
        option_support=True,
        option_adfree=True,
    )
    payment.save()
    code_object.delete()
    LOG.info("%s code redeemed on draw %s", code, draw_id)
    return Response()


@api_view(["POST"])
def instagram_preview(request):
    LOG.info("Fetching instagram info for: %s", request.data)
    serializer = serializers.InstagramPreviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    post_url = data["url"]
    try:
        preview = instagram.get_preview(post_url)
    except instagram.InvalidURL:
        raise ValidationError(f"Invalid post URL: {post_url}") from None
    except instagram.NotFoundError:
        raise ValidationError(f"Post not found: {post_url}") from None
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise APIException("Timed-out. Try again later.") from None
    return Response(
        {
            "post_pic": preview.post_pic,
            "user_name": preview.user_name,
            "user_pic": preview.user_pic,
            "comment_count": preview.comment_count,
        }
    )
