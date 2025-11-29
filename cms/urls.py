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

    path('mapping_jadwal/', mapping_jadwal, name='mapping_jadwal'),
    path('buat_jadwal/', buat_jadwal, name='buat_jadwal'),
    path('save_jadwal/', save_jadwal, name='save_jadwal'),
    path('edit_jadwal/<str:divisi_id>/<int:tahun>/<str:bulan>', edit_jadwal, name='edit_jadwal'),
    path('update_jadwal/', update_jadwal, name='update_jadwal'),

    path('absen/', index_absen, name='absen'),
    path('absen/<str:divisi_id>', absen, name='absen'),

    path('cuti_master/', cuti_master, name='cuti_master'),
    path('addCuti/', addCuti, name='addCuti'),
    path('editCuti/<str:id>', editCuti, name='editCuti'),
    path('deleteCuti/<str:id>', deleteCuti, name='deleteCuti'),

    path('persetujuan_cuti/', persetujuan_cuti, name='persetujuan_cuti'),
    path('detail_pengajuan/<int:id>', detail_pengajuan, name='detail_pengajuan'),

    path('karyawan/', karyawan, name='karyawan'),
    path('detail_karyawan/<str:nik>', detail_karyawan, name='detail_karyawan'),
    path('editKaryawan/<str:nik>', editKaryawan, name='editKaryawan'),
    path('deleteKaryawan/<str:nik>', deleteKaryawan, name='deleteKaryawan'),

    path('err403/', err403, name='err403')
]