from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),

    path('dashboard/', dashboard, name='dashboard'),
    path('divisi_master/', divisi_master, name='divisi_master'),
    path('addDivisi/', addDivisi, name='addDivisi'),
    path('editDivisi/<str:id>', editDivisi, name='editDivisi'),
    path('deleteDivisi/<str:id>', deleteDivisi, name='deleteDivisi'),

    path('jadwal_master/', jadwal_master, name='jadwal_master'),
    path('addJadwal/', addJadwal, name='addJadwal'),
    path('editJadwal/<str:id>', editJadwal, name='editJadwal'),
    path('deleteJadwal/<str:id>', deleteJadwal, name='deleteJadwal'),

    path('addUser/', addUser, name='addUser'),
]