from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login, name='login'),

    path('dashboard/', dashboard, name='dashboard'),

    path('komponen_gaji/', komponen_gaji, name='komponen_gaji'),
    path('komponen_gaji/add/', add_komponen_gaji, name='add_komponen_gaji'),
    path('komponen_gaji/edit/<int:id>/', edit_komponen_gaji, name='edit_komponen_gaji'),
    path('komponen_gaji/delete/<int:id>/', delete_komponen_gaji, name='delete_komponen_gaji'),

    path('karyawan/', karyawan, name='karyawan'),
    path('karyawan/detail_gaji/<int:nik>/', detail_gaji, name='detail_gaji'),
]