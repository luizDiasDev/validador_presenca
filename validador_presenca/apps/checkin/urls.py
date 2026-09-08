from django.urls import path
from . import views

app_name = "checkin"
# url micro
urlpatterns = [
    path('',views.qr_demo,name='qr_demo')
]
