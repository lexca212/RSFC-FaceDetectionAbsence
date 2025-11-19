from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect , get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.contrib import messages
from .decorators import login_auth
from app.models import *
from .models import *
import base64

# Create your views here.

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        try:
            user = get_object_or_404(Admins, username=username)

            if check_password(password, user.password):
              request.session['nik_id'] = user.nik_id
              return redirect('/admins/dashboard')
        except Admins.DoesNotExist:
            messages.error(request, 'Invalid username or password')
            return redirect('/admins/login') 
    return render(request, 'admin/login.html')

def logout(request):
    try:
        del request.session['nik_id']
    except KeyError:
        pass
    return redirect('/admins/login')

@login_auth
def dashboard(request):
    # del request.session['nik_id']
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    context = {
      'user': user,
      'title': 'Dashboard'
    }

    return render(request, 'admin/dashboard.html', context)

@login_auth
def divisi_master(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    divisi_list = MasterDivisions.objects.all()

    context = {
      'user': user,
      'title': 'Divisi Master',
      'divisi_list': divisi_list, 
    }

    return render(request, 'admin/divisi_master/index.html', context)

@login_auth
def addDivisi(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      divisi_id = request.POST['divisi_id']
      divisi_name = request.POST['divisi_name']

      divisi_list = MasterDivisions.objects.all()

      for divisi in divisi_list:
          if divisi.id == divisi_id:
              messages.error(request, 'Divisi sudah ada.')
              return redirect('/admins/addDivisi')

      # Create new data entry
      divisi = MasterDivisions(
          id=divisi_id,
          name=divisi_name,
      )
      divisi.save()

      messages.success(request, 'Data divisi berhasil diupload.')
      return redirect('/admins/divisi_master')
    
    context = {
      'user': user,
      'title': 'Tambah Divisi',
    }
    return render(request, 'admin/divisi_master/addForm.html', context)

@login_auth
def editDivisi(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      divisi_id = request.POST['divisi_id']
      divisi_name = request.POST['divisi_name']

      try:
        divisi = get_object_or_404(MasterDivisions, id=divisi_id)

        divisi.name = divisi_name
        divisi.save()

        messages.success(request, 'Data divisi berhasil diupdate.')
        return redirect('/admins/divisi_master')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data divisi: {e}')
        return redirect('/admins/divisi_master')
    
    divisi = get_object_or_404(MasterDivisions, id=id)

    context = {
      'user': user,
      'title': 'Edit Divisi',
      'divisi': divisi,
    }
    return render(request, 'admin/divisi_master/editForm.html', context)

def deleteDivisi(request, id):
    try:
      divisi = get_object_or_404(MasterDivisions, id=id)
      divisi.delete()

      messages.success(request, 'Data divisi berhasil dihapus.')
      return redirect('/admins/divisi_master')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data divisi: {e}')
      return redirect('/admins/divisi_master')
    
@login_auth
def jadwal_master(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    jadwal_list = MasterSchedules.objects.all()

    context = {
      'user': user,
      'title': 'Jadwal Master',
      'jadwal_list': jadwal_list, 
    }

    return render(request, 'admin/jadwal_master/index.html', context)

def addJadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      id = request.POST['jadwal_id']
      name = request.POST['jadwal_name']
      start_time = request.POST['jam_masuk']
      end_time = request.POST['jam_keluar']

      # Create new data entry
      jadwal = MasterSchedules(
          id=id,
          name=name,
          start_time=start_time,
          end_time=end_time,
      )
      jadwal.save()

      messages.success(request, 'Data jadwal berhasil diupload.')
      return redirect('/admins/jadwal_master')
    
    context = {
      'user': user,
      'title': 'Tambah Jadwal',
    }
    return render(request, 'admin/jadwal_master/addForm.html', context)

@login_auth
def editJadwal(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      jadwal_id = request.POST['jadwal_id']
      jadwal_name = request.POST['jadwal_name']
      start_time = request.POST['jam_masuk']
      end_time = request.POST['jam_keluar']

      try:
        jadwal = get_object_or_404(MasterSchedules, id=jadwal_id)

        jadwal.name = jadwal_name
        jadwal.start_time = start_time
        jadwal.end_time = end_time
        jadwal.save()

        messages.success(request, 'Data jadwal berhasil diupdate.')
        return redirect('/admins/jadwal_master')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data jadwal: {e}')
        return redirect('/admins/jadwal_master')
    
    jadwal = get_object_or_404(MasterSchedules, id=id)

    context = {
      'user': user,
      'title': 'Edit Jadwal',
      'jadwal': jadwal,
    }
    return render(request, 'admin/jadwal_master/editForm.html', context)

@login_auth
def deleteJadwal(request, id):
    try:
      jadwal = get_object_or_404(MasterSchedules, id=id)
      jadwal.delete()

      messages.success(request, 'Data jadwal berhasil dihapus.')
      return redirect('/admins/jadwal_master')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data jadwal: {e}')
      return redirect('/admins/jadwal_master')
    
@login_auth
def addUser(request):
    if request.method == 'POST':
      nik = request.POST['nik']
      name = request.POST['name']
      divisi = request.POST['divisi']
      photo_data = request.POST.get('photo', '')

      if photo_data:
        try:
          # Decode base64 image from the photo data
          format, imgstr = photo_data.split(';base64,')
          ext = format.split('/')[-1]
          data = ContentFile(base64.b64decode(imgstr), name=f'{nik}.{ext}')

          # Create new data entry
          user = Users(
              nik=nik,
              name=name,
              divisi=divisi,
              photo=data,
          )
          user.save()

          messages.success(request, 'Data karyawan berhasil diupload.')
          return redirect('/admins/addUser')
        except Exception as e:
            messages.error(request, f'Gagal mengupload data karyawan: {e}')
      else:
        messages.error(request, 'Foto tidak tersedia atau tidak valid.')

      return redirect('/admins/addUser')
    
    divisi_list = MasterDivisions.objects.all()
    context = {
      'divisi_list': divisi_list
    }
    return render(request, 'admin/addUser.html', context)
