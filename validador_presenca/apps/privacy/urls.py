from django.urls import path
from . import views

app_name = "privacy"

urlpatterns = [
    path("", views.central_privacidade, name="central"),
    path("politica/", views.politica_privacidade, name="politica_privacidade"),
    path("termos/", views.termo_uso, name="termo_uso"),
    path("termo-biometrico/", views.termo_biometrico, name="termo_biometrico"),
    path("solicitar/", views.solicitar_direito, name="solicitar_direito"),
    path("minhas-solicitacoes/", views.minhas_solicitacoes, name="minhas_solicitacoes"),
    path("meus-dados.json", views.baixar_meus_dados, name="baixar_meus_dados"),
    path("solicitacoes/", views.solicitacoes_admin, name="solicitacoes_admin"),
    path("solicitacoes/<int:solicitacao_id>/decidir/", views.decidir_solicitacao, name="decidir_solicitacao"),
]