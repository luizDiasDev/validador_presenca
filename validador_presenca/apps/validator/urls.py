from django.urls import path
from . import views

app_name = "validator"

urlpatterns = [
    path('', views.painel, name="painel")
]