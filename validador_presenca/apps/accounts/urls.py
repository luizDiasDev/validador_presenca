from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AdsumLoginView.as_view(template_name="accounts/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", views.AdsumLogoutView.as_view(next_page="accounts:login"), name="logout"),
    path("2fa/configurar/", views.config_totp, name="config_totp"),
    path("2fa/verificar/", views.read_totp, name="read_totp"),
]