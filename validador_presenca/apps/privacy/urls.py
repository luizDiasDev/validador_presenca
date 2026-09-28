from django.urls import path
from . import views

app_name = "privacy"

urlpatterns = [
    path("", views.central_privacidade, name="central"),
    path("politica/", views.politica_privacidade, name="politica_privacidade"),
    path("termos/", views.termo_uso, name="termo_uso"),
    path("solicitar/", views.solicitar_direito, name="solicitar_direito"),
    path("minhas-solicitacoes/", views.minhas_solicitacoes, name="minhas_solicitacoes"),
]