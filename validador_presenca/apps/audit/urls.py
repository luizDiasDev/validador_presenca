from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    path("", views.registro_de_atividades, name="registro"),
]
