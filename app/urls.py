from django.urls import path
from .views import *

urlpatterns = [
    path('absence/', absence, name='absence'),
]