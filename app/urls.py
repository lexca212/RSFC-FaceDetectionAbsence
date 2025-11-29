from django.urls import path
from .views import *

urlpatterns = [
    path('absence/', absence, name='absence'),

    path('pengajuan_cuti/', pengajuan_cuti, name='pengajuan_cuti'),
    path('edit_pengajuan_cuti/<int:id>', edit_pengajuan_cuti, name='edit_pengajuan_cuti'),
    path('delete_pengajuan_cuti/<int:id>', delete_pengajuan_cuti, name='delete_pengajuan_cuti'),

    path('jadwal/', jadwal, name='jadwal'),
    path('presensi/', presensi, name='presensi'),

    path('profile/<str:nik>', profile, name='profile')
]