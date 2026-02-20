from django.contrib import admin
from django.urls import path, include

from simpsonsRankApp.views import do_login

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("simpsonsRankApp.urls")),
    path("simpsonsRankApp/", include("simpsonsRankApp.urls")),
    path("login/", do_login, name="login"),
]