from django.urls import path
from .views import *

urlpatterns = [
    path('choose_mode/', choose_mode, name='choose_mode'),
    path('absensi/', absence, name='absence'),
    path('absensi/konfirmasi/', confirm_absence, name='confirm_absence'),
    path('absensi/konfirmasi_lembur/', confirm_overtime, name='confirm_overtime'),

    path('pengajuan_cuti/', pengajuan_cuti, name='pengajuan_cuti'),
    path('pengajuan_cuti/edit/<int:id>', edit_pengajuan_cuti, name='edit_pengajuan_cuti'),
    path('pengajuan_cuti/delete/<int:id>', delete_pengajuan_cuti, name='delete_pengajuan_cuti'),

    path('jadwal/', jadwal, name='jadwal'),
    path('presensi/', presensi, name='presensi'),

    path('pengajuan_izin/', pengajuan_izin, name='pengajuan_izin'),
    path('pengajuan_izin/edit/<int:id>', edit_pengajuan_izin, name='edit_pengajuan_izin'),
    path('pengajuan_izin/delete/<int:id>', delete_pengajuan_izin, name='delete_pengajuan_izin'),

    path('keluar_bentar/', keluar_bentar, name='keluar_bentar'),
    path('keluar_bentar/balik', balik_keluar_bentar, name='balik_keluar_bentar'),

    path('profil/<str:nik>', profile, name='profile'),

    path('pengajuan_lembur/', pengajuan_lembur, name='pengajuan_lembur'),
    path('pengajuan_lembur/<int:id>', detail_pengajuan_lembur, name='detail_pengajuan_lembur'),

    path('save_fcm_token/', save_fcm_token, name='save_fcm_token')
]