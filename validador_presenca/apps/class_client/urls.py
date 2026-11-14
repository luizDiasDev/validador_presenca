from django.urls import path

from . import views

app_name = "class_client"

urlpatterns = [
    path("qr/", views.current_qr, name="qr"),
    path("autorizacao/", views.pending_authorization, name="autorizacao"),
    path("rosto/", views.submit_face, name="rosto"),
]
