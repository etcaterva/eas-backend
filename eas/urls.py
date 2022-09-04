from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path, re_path

urlpatterns = []

if settings.ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))

urlpatterns += [
    re_path("^api/", include("eas.api.urls")),
]
