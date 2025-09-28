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
router.register(r"tiktok", views.TiktokViewSet, basename="tiktok")
router.register(r"shifts", views.ShiftsViewSet, basename="shifts")
urlpatterns = [
    re_path(
        r"instagram-preview/$",
        views.instagram_preview,
        name="instagram-preview",
    ),
    re_path(
        r"promo-code/redeem/$",
        views.redeem_promo_code,
        name="redeem-promo-code",
    ),
    re_path(r"paypal/create/", views.paypal_create, name="paypal-create"),
    re_path(r"paypal/accept/", views.paypal_accept, name="paypal-accept"),
    re_path(r"revolut/create/", views.revolut_create, name="revolut-create"),
    re_path(
        r"revolut/accept/(?P<draw_id>[^/]+)/$",
        views.revolut_accept,
        name="revolut-accept",
    ),
    re_path(
        r"secret-santa-admin/(?P<pk>[^/]+)/$",
        views.secret_santa_admin,
        name="secret-santa-admin",
    ),
    re_path(
        r"secret-santa-admin/(?P<draw_pk>[^/]+)/(?P<result_pk>[^/]+)/$",
        views.secret_santa_resend_email,
        name="secret-santa-resend-email",
    ),
    # Authentication endpoints
    re_path(r"auth/login/$", views.request_magic_link, name="request-magic-link"),
    re_path(r"auth/verify/$", views.verify_magic_link, name="verify-magic-link"),
    re_path(r"auth/user/$", views.current_user, name="current-user"),
    re_path(r"auth/logout/$", views.logout_user, name="logout"),
    re_path(r"auth/tiers/$", views.subscription_tiers, name="subscription-tiers"),
    re_path(
        r"auth/subscription/create/$",
        views.create_subscription,
        name="create-subscription",
    ),
    re_path(
        r"auth/subscription/accept/$",
        views.accept_subscription,
        name="accept-subscription",
    ),
    *router.urls,
]
