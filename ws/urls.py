from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'random_number', views.RandomNumber, base_name='random_number')
urlpatterns = router.urls
