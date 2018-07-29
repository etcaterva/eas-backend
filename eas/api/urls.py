from rest_framework.routers import DefaultRouter

from . import views

# pylint: disable=invalid-name

# api endpoints

router = DefaultRouter()
router.register(r'random_number', views.RandomNumberViewSet,
                base_name='random_number')
router.register(r'raffle', views.RaffleViewSet,
                base_name='raffle')
router.register(r'lottery', views.LotteryViewSet,
                base_name='lottery')
router.register(r'groups', views.GroupsViewSet,
                base_name='groups')
router.register(r'spinner', views.SpinnerViewSet,
                base_name='spinner')
router.register(r'letter', views.LetterViewSet,
                base_name='letter')
router.register(r'coin', views.CoinViewSet,
                base_name='coin')
urlpatterns = router.urls
