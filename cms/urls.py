from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login, name='login'),

    path('dashboard/', dashboard, name='dashboard'),
    path('divisi_master/', divisi_master, name='divisi_master'),
    path('addDivisi/', addDivisi, name='addDivisi'),
    path('editDivisi/<str:id>', editDivisi, name='editDivisi'),
    path('deleteDivisi/<str:id>', deleteDivisi, name='deleteDivisi'),

    path('addUser/', addUser, name='addUser'),
]