from django.urls import path
from . import views

app_name = "checkin"
# url micro
urlpatterns = [
    path("", views.qr_demo, name="qr_demo"),
    path(
        "api/v1/sessoes/sala/<int:sala_id>/status/",
        views.status_sessao_sala,
        name="status_sessao_sala",
    ),
]