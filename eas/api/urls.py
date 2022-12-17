from django.urls import re_path
from rest_framework.routers import DefaultRouter

from . import views

# pylint: disable=invalid-name

# api endpoints

router = DefaultRouter()
router.register(r"random_number", views.RandomNumberViewSet, basename="random_number")
router.register(r"raffle", views.RaffleViewSet, basename="raffle")
router.register(r"lottery", views.LotteryViewSet, basename="lottery")
router.register(r"groups", views.GroupsViewSet, basename="groups")
router.register(r"tournament", views.TournamentViewSet, basename="tournament")
router.register(r"spinner", views.SpinnerViewSet, basename="spinner")
router.register(r"letter", views.LetterViewSet, basename="letter")
router.register(r"coin", views.CoinViewSet, basename="coin")
router.register(r"link", views.LinkViewSet, basename="link")
router.register(r"secret-santa", views.SecretSantaSet, basename="secret-santa")
router.register(r"instagram", views.InstagramViewSet, basename="instagram")
urlpatterns = [
    re_path(r"paypal/create/", views.paypal_create, name="paypal-create"),
    re_path(r"paypal/accept/", views.paypal_accept, name="paypal-accept"),
    *router.urls,
]
