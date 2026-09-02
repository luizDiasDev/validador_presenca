from django.urls import path
from . import views

app_name = 'checkin'

# url micro
urlpatterns = [
    path('',views.index,name='index')
]
