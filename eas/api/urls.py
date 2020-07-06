from rest_framework.routers import DefaultRouter

from . import views

# pylint: disable=invalid-name

# api endpoints

router = DefaultRouter()
router.register(r"random_number", views.RandomNumberViewSet, basename="random_number")
router.register(r"raffle", views.RaffleViewSet, basename="raffle")
router.register(r"lottery", views.LotteryViewSet, basename="lottery")
router.register(r"groups", views.GroupsViewSet, basename="groups")
router.register(r"spinner", views.SpinnerViewSet, basename="spinner")
router.register(r"letter", views.LetterViewSet, basename="letter")
router.register(r"coin", views.CoinViewSet, basename="coin")
urlpatterns = router.urls
