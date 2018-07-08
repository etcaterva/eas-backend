from django.urls import re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
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

# schema definition
api_info = openapi.Info(
    title="EAS API",
    default_version="v1",
)

schema_view = get_schema_view(
    api_info,
    validators=['flex', 'ssv'],
    public=True,
)

urlpatterns += [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=None), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=None),
            name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=None),
            name='schema-redoc'),
]
