from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.urls import path

urlpatterns = []

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))

urlpatterns += [
    url("^api/", include("eas.api.urls")),
]
