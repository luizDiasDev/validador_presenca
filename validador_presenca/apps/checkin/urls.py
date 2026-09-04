from django.urls import path
from . import views

# url micro
urlpatterns = [
    path('',views.index,name='index')
]
