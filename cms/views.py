from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect , get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.contrib import messages
from .decorators import login_auth
from app.models import *
from .models import *
import calendar
import datetime
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

@login_auth
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

@login_auth
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

@login_auth
def mapping_jadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    divisi_list = MasterDivisions.objects.all().order_by('name')

    today = datetime.date.today()

    bulan_ini = today.month
    tahun_ini = today.year

    if bulan_ini == 12:
        bulan_depan = 1
        tahun_depan = tahun_ini + 1
    else:
        bulan_depan = bulan_ini + 1
        tahun_depan = tahun_ini

    hasil = {}

    for divisi in divisi_list:
        hasil[divisi.id] = {}

        semua_jadwal = MappingSchedules.objects.filter(
            nik__divisi=divisi.id,
            date__month__in=[bulan_ini, bulan_depan],
            date__year__in=[tahun_ini, tahun_depan]
        ).select_related('nik', 'schedule').order_by('nik__name', 'date')

        for jadwal in semua_jadwal:
            tahun = jadwal.date.year
            bulan = jadwal.date.month
            hari = jadwal.date.day
            nik = jadwal.nik.nik
            nama = jadwal.nik.name

            bulan_text = calendar.month_name[bulan]

            hasil[divisi.id].setdefault(tahun, {})
            hasil[divisi.id][tahun].setdefault(bulan_text, {})

            total_hari = calendar.monthrange(tahun, bulan)[1]

            hasil[divisi.id][tahun][bulan_text].setdefault(nik, {
                "nama": nama,
                "days": {d: "-" for d in range(1, total_hari + 1)}
            })

            hasil[divisi.id][tahun][bulan_text][nik]["days"][hari] = jadwal.schedule.name

    context = {
        'user': user,
        'title': 'Jadwal Karyawan',
        'data_jadwal': hasil,
        'divisi_list': divisi_list
    }
    return render(request, "admin/mapping/index.html", context)

@login_auth
def buat_jadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    bulan = request.POST['bulan']
    tahun = request.POST['tahun']
    divisi = request.POST['divisi']

    if not bulan or not tahun:
        return render(request, "jadwal/pilih_bulan.html")

    bulan = int(bulan)
    tahun = int(tahun)

    _, jumlah_hari = calendar.monthrange(tahun, bulan)
    tanggal_list = list(range(1, jumlah_hari + 1))

    schedules = MasterSchedules.objects.all()

    users = Users.objects.filter(divisi=divisi)

    bulan_text = calendar.month_name[bulan]

    context = {
        "user": user,
        "title": "Buat Jadwal Karyawan",
        "bulan": bulan,
        "tahun": tahun,
        "bulan_text": bulan_text,
        "tanggal_list": tanggal_list,
        "users": users,
        "schedules": schedules,
    }

    return render(request, "admin/mapping/addForm.html", context)

@login_auth
def save_jadwal(request):
    if request.method == "POST":
        bulan = int(request.POST['bulan'])
        tahun = int(request.POST['tahun'])

        _, jumlah_hari = calendar.monthrange(tahun, bulan)
        tanggal_list = list(range(1, jumlah_hari + 1))

        users = Users.objects.all()

        for user in users:
            for tgl in tanggal_list:
                shift_key = f'shift_{user.nik}_{tgl}'
                shift_id = request.POST.get(shift_key)

                if shift_id:
                    date_str = f"{tahun}-{bulan:02d}-{tgl:02d}"
                    shift = MasterSchedules.objects.filter(id=shift_id).first()

                    if shift:
                        if shift.name == 'Libur':
                            from datetime import datetime
                            date = datetime.strptime(date_str, "%Y-%m-%d")
                            is_there = InAbsences.objects.filter(
                                nik=user,
                                date_in__date=date.date(),
                                status_in="Libur"
                            ).exists()

                            print(f'{is_there}')

                            if not is_there:
                                InAbsences.objects.create(
                                    nik=user,
                                    date_in=date_str,
                                    status_in="Libur",
                                    schedule=shift,
                                    date_out=date_str,
                                    status_out="Libur"
                                )

                    mapping, created = MappingSchedules.objects.get_or_create(
                        id=f"{user.nik}_{date_str}",
                        nik=user,
                        date=date_str,
                        defaults={'schedule_id': shift_id}
                    )

                    if not created:
                        mapping.schedule_id = shift_id
                        mapping.save()

        messages.success(request, 'Jadwal karyawan berhasil disimpan.')
        return redirect('/admins/mapping_jadwal')
   
@login_auth
def edit_jadwal(request, divisi_id, tahun, bulan):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    from datetime import datetime

    bulan = datetime.strptime(bulan, "%B").month

    _, jumlah_hari = calendar.monthrange(tahun, bulan)
    tanggal_list = list(range(1, jumlah_hari + 1))

    schedules = MasterSchedules.objects.all()

    users = Users.objects.filter(divisi=divisi_id)

    mapping = MappingSchedules.objects.filter(
        nik__divisi=divisi_id,
        date__year=tahun,
        date__month=bulan
    ).select_related('nik', 'schedule')

    jadwal = {}

    for item in mapping:
        nik = item.nik.nik
        hari = item.date.day
        schedule_id = item.schedule.id

        if nik not in jadwal:
            jadwal[nik] = {}

        jadwal[nik][hari] = schedule_id

    bulan_text = calendar.month_name[bulan]

    context = {
        "user": user,
        "title": "Edit Jadwal Karyawan",
        "bulan": bulan,
        "tahun": tahun,
        "bulan_text": bulan_text,
        "tanggal_list": tanggal_list,
        "users": users,
        "schedules": schedules,
        "jadwal_lama": jadwal
    }

    return render(request, "admin/mapping/editForm.html", context)

@login_auth  
def update_jadwal(request):
    if request.method == "POST":
        bulan = int(request.POST['bulan'])
        tahun = int(request.POST['tahun'])

        _, jumlah_hari = calendar.monthrange(tahun, bulan)
        tanggal_list = list(range(1, jumlah_hari + 1))

        users = Users.objects.all()

        for user in users:
            for tgl in tanggal_list:

                shift_key = f"shift_{user.nik}_{tgl}"
                shift_id = request.POST.get(shift_key) 

                shift = MasterSchedules.objects.filter(id=shift_id).first()

                date_str = f"{tahun}-{bulan:02d}-{tgl:02d}"
                mapping_id = f"{user.nik}_{date_str}"

                try:
                    mapping = MappingSchedules.objects.get(id=mapping_id)
                    mapping_exists = True
                except MappingSchedules.DoesNotExist:
                    mapping = None
                    mapping_exists = False


                if shift_id:
                    if shift:
                        if shift.name == 'Libur':
                            from datetime import datetime
                            date = datetime.strptime(date_str, "%Y-%m-%d")
                            is_there = InAbsences.objects.filter(
                                nik=user,
                                date_in__date=date.date(),
                                status_in="Libur"
                            ).exists()

                            print(f'{is_there}')

                            if not is_there:
                                InAbsences.objects.create(
                                    nik=user,
                                    date_in=date_str,
                                    status_in="Libur",
                                    schedule=shift,
                                    date_out=date_str,
                                    status_out="Libur"
                                )
                    if mapping_exists:
                        mapping.schedule_id = shift_id
                        mapping.save()
                    else:
                        MappingSchedules.objects.create(
                            id=mapping_id,
                            nik=user,
                            date=date_str,
                            schedule_id=shift_id
                        )
                else:
                    if mapping_exists:
                        mapping.delete()

        messages.success(request, "Jadwal karyawan berhasil diperbarui.")
        return redirect('/admins/mapping_jadwal')

@login_auth
def index_absen(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    divisi_list = MasterDivisions.objects.all()

    context = {
        'user': user,
        'divisi_list': divisi_list,
        'title': 'Dashboard Absen'
    }

    return render(request, 'admin/absen/index.html', context)

@login_auth
def absen(request, divisi_id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    list_absen = InAbsences.objects.filter(
        nik__divisi=divisi_id
    ).select_related('nik')

    absensi_per_bulan = {}

    from datetime import datetime

    for absen in list_absen:
        bulan_key = absen.date_in.strftime("%Y-%m")
        
        if bulan_key not in absensi_per_bulan:
            absensi_per_bulan[bulan_key] = []

        absensi_per_bulan[bulan_key].append(absen)

    absensi_per_bulan[bulan_key].append

    bulan_labels = {
        key: datetime.strptime(key, "%Y-%m").strftime("%B %Y")
        for key in absensi_per_bulan.keys()
    }

    context = {
        'user': user,
        'divisi_id': divisi_id,
        'absensi_per_bulan': absensi_per_bulan,
        'bulan_labels': bulan_labels,      
        'title': f'Absen Divisi {divisi_id}',
    }

    return render(request, 'admin/absen/list_absen.html', context)

   