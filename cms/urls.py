from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login, name='login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('divisi_master/', divisi_master, name='divisi_master'),
    path('addUser/', addUser, name='addUser'),
]