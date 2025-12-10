from django.urls import path
from .views import *

urlpatterns = [
    path('absensi/', absence, name='absence'),

    path('pengajuan_cuti/', pengajuan_cuti, name='pengajuan_cuti'),
    path('pengajuan_cuti/edit/<int:id>', edit_pengajuan_cuti, name='edit_pengajuan_cuti'),
    path('pengajuan_cuti/delete/<int:id>', delete_pengajuan_cuti, name='delete_pengajuan_cuti'),

    path('jadwal/', jadwal, name='jadwal'),
    path('presensi/', presensi, name='presensi'),

    path('profil/<str:nik>', profile, name='profile')
]