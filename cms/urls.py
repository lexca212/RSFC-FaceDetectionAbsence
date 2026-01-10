from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login, name='login'),
    path('logout/', logout, name='logout'),

    path('dashboard/', dashboard, name='dashboard'),

    path('divisi/', divisi_master, name='divisi_master'),
    path('divisi/add/', addDivisi, name='addDivisi'),
    path('divisi/edit/<str:id>', editDivisi, name='editDivisi'),
    path('divisi/delete/<str:id>', deleteDivisi, name='deleteDivisi'),

    path('jadwal/', jadwal_master, name='jadwal_master'),
    path('jadwal/add/', addJadwal, name='addJadwal'),
    path('jadwal/edit/<str:id>', editJadwal, name='editJadwal'),
    path('jadwal/delete/<str:id>', deleteJadwal, name='deleteJadwal'),

    path('addUser/', addUser, name='addUser'),

    path('mapping_jadwal/', mapping_jadwal, name='mapping_jadwal'),
    path('mapping_jadwal/add/', buat_jadwal, name='buat_jadwal'),
    path('mapping_jadwal/save/', save_jadwal, name='save_jadwal'),
    path('mapping_jadwal/edit/<str:divisi_id>/<int:tahun>/<str:bulan>', edit_jadwal, name='edit_jadwal'),
    path('mapping_jadwal/update/', update_jadwal, name='update_jadwal'),

    path('absen/', index_absen, name='absen'),
    path('absen/<str:divisi_id>', absen, name='absen'),

    path('cuti/', cuti_master, name='cuti_master'),
    path('cuti/add/', addCuti, name='addCuti'),
    path('cuti/edit/<str:id>', editCuti, name='editCuti'),
    path('cuti/delete/<str:id>', deleteCuti, name='deleteCuti'),

    path('persetujuan_cuti/', persetujuan_cuti, name='persetujuan_cuti'),
    path('persetujuan_cuti/<int:id>', detail_pengajuan, name='detail_pengajuan'),

    path('karyawan/', karyawan, name='karyawan'),
    path('karyawan/<str:nik>', detail_karyawan, name='detail_karyawan'),
    path('karyawan/edit/<str:nik>', editKaryawan, name='editKaryawan'),
    path('karyawan/delete/<str:nik>', deleteKaryawan, name='deleteKaryawan'),

    path('izin/', izin_master, name='izin_master'),
    path('izin/add/', addIzin, name='addIzin'),
    path('izin/edit/<str:id>', editIzin, name='editIzin'),
    path('izin/delete/<str:id>', deleteIzin, name='deleteIzin'),

    path('persetujuan_izin/', persetujuan_izin, name='persetujuan_izin'),
    path('persetujuan_izin/<int:id>', detail_pengajuan_izin, name='detail_pengajuan_izin'),

    path('riwayat_keluar/', riwayat_keluar, name='riwayat_keluar'),

    path('rekap_kehadiran/', rekap_kehadiran, name='rekap_kehadiran'),
    path('rekap_kehadiran/<str:nik>/', rekap_kehadiran_detail, name='rekap_kehadiran_detail'),

    path('err403/', err403, name='err403'),
    path('err404/', err404, name='err404')
]