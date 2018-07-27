from rest_framework.routers import DefaultRouter

from . import views

# pylint: disable=invalid-name

# api endpoints

router = DefaultRouter()
router.register(r'random_number', views.RandomNumberViewSet,
                base_name='random_number')
router.register(r'raffle', views.RaffleViewSet,
                base_name='raffle')
urlpatterns = router.urls
