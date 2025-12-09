from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect , get_object_or_404
from django.core.files.base import ContentFile
from django.http import HttpResponseNotFound
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from .decorators import *
from app.models import *
import face_recognition
from .models import *
import calendar
import datetime
import base64
import pickle
import io

# Create your views here.

def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        if not email or not password:
            messages.error(request, 'email and password are required')
            return redirect('/admins/login')

        user = Users.objects.filter(email=email).first()

        if user is None:
            messages.error(request, 'Your email is not registerd')
            return redirect('/admins/login')

        if not check_password(password, user.password):
            messages.error(request, 'Your password is invalid')
            return redirect('/admins/login')

        request.session['nik_id'] = user.nik
        request.session['is_admin'] = user.is_admin

        if user.is_admin == 2:
            return redirect('/admins/dashboard')
        elif user.is_admin == 1:
            return redirect('/admins/mapping_jadwal')
        else:
            return redirect('/users/jadwal')

    return render(request, 'admin/login.html')

def logout(request):
    try:
        del request.session['nik_id']
    except KeyError:
        pass
    return redirect('/admins/login')

def err403(request):
    return render(request, 'admin/403.html')

def err404(request, exception, template_name='admin/404.html'):
    response = render(request, template_name)
    response.status_code = 404
    return response

@login_auth 
@admin_required
@superadmin_required
def dashboard(request):
    # del request.session['nik_id']
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    context = {
      'user': user,
      'title': 'Dashboard'
    }

    return render(request, 'admin/dashboard.html', context)

@login_auth
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
def addUser(request):
    if request.method == 'POST':
        nik = request.POST['nik']
        name = request.POST['name']
        email = request.POST['email']
        password = request.POST['password']
        divisi = request.POST['divisi']
        photo_data = request.POST.get('photo', '')

        hash_password = make_password(password)

        if photo_data:
            try:
                format, imgstr = photo_data.split(';base64,')
                ext = format.split('/')[-1]
                img_bytes = base64.b64decode(imgstr)
                
                photo_file = ContentFile(img_bytes, name=f'{nik}.{ext}')

                image_stream = io.BytesIO(img_bytes)
                loaded_image = face_recognition.load_image_file(image_stream, mode='RGB')
                
                encodings = face_recognition.face_encodings(loaded_image)

                if len(encodings) == 0:
                    messages.error(request, 'Wajah tidak terdeteksi dalam foto. Pendaftaran dibatalkan.')
                    return redirect('/admins/addUser')
                
                face_enc = encodings[0] 
                
                serialized_encoding = pickle.dumps(face_enc)
                
                user = Users(
                    nik=nik,
                    name=name,
                    email=email,
                    password=hash_password,
                    divisi=divisi,
                    photo=photo_file, 
                    face_encoding=serialized_encoding 
                )
                user.save()

                messages.success(request, 'Data karyawan berhasil diupload dan encoding wajah disimpan.')
                return redirect('/admins/addUser')
            
            except Exception as e:
                messages.error(request, f'Gagal mengupload data karyawan atau menghitung encoding: {e}')
                print(f"Error detail: {e}") 
                return redirect('/admins/addUser')
                
        else:
            messages.error(request, 'Foto tidak tersedia atau tidak valid.')

        return redirect('/admins/addUser')
    
    divisi_list = MasterDivisions.objects.all()
    context = {
      'divisi_list': divisi_list
    }
    return render(request, 'admin/addUser.html', context)

@login_auth
@admin_required
def mapping_jadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    divisi_list = MasterDivisions.objects.filter(id=user.divisi)

    if user.is_admin == 2:
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
@admin_required
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

    schedules = MasterSchedules.objects.exclude(id='CUTI').all()

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
@admin_required
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
@admin_required
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
@admin_required
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
                    if shift and shift.name == 'Libur':
                        from datetime import datetime
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        is_there = InAbsences.objects.filter(
                            nik=user,
                            date_in__date=date.date(),
                            status_in="Libur"
                        ).exists()

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
@admin_required
@superadmin_required
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
@admin_required
@superadmin_required
def absen(request, divisi_id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')

    list_absen = (
        InAbsences.objects.filter(nik__divisi=divisi_id)
        .select_related('nik', 'schedule')
        .order_by('date_in').order_by('nik')
    )

    if selected_month and selected_year:
        list_absen = list_absen.filter(
            date_in__month=selected_month,
            date_in__year=selected_year
        )

    absensi_per_bulan = {}

    from datetime import datetime, timedelta

    for absen in list_absen:
        bulan_key = absen.date_in.strftime("%Y-%m")

        late_minutes = 0
        late_time = None

        if absen.schedule and absen.schedule.start_time:

            scheduled_naive = datetime.combine(
                absen.date_in.date(),
                absen.schedule.start_time
            )
            from django.utils import timezone

            scheduled_in = timezone.make_aware(
                scheduled_naive,
                timezone.get_current_timezone()
            )

            actual_in = absen.date_in

            diff_seconds = (actual_in - scheduled_in).total_seconds()

            if diff_seconds > 0:
                late_minutes = int(diff_seconds // 60)
                late_time = str(timedelta(minutes=late_minutes))

        absen.late_minutes = late_minutes
        absen.late_time = late_time

        total_work = None
        total_minutes = 0

        if absen.date_out:

            actual_in = absen.date_in
            actual_out = absen.date_out

            diff_seconds = (actual_out - actual_in).total_seconds()

            if diff_seconds > 0:
                total_minutes = int(diff_seconds // 60)
                total_work = str(timedelta(minutes=total_minutes))

        if absen.schedule.id == 'CUTI' or absen.schedule.id == 'LIBUR':
            total_work = '00:00:00'
            total_minutes = 0
        
        absen.total_work = total_work
        absen.total_work_minutes = total_minutes

        if bulan_key not in absensi_per_bulan:
            absensi_per_bulan[bulan_key] = []

        absensi_per_bulan[bulan_key].append(absen)

    absensi_per_bulan = dict(sorted(
        absensi_per_bulan.items(),
        key=lambda x: x[0], 
        reverse=True
    )[:6])

    bulan_labels = {
        key: datetime.strptime(key, "%Y-%m").strftime("%B %Y")
        for key in absensi_per_bulan.keys()
    }

    month_list = [(f"{i:02}", calendar.month_name[i]) for i in range(1, 13)]
    year_list = InAbsences.objects.dates('date_in', 'year')

    divisi = get_object_or_404(MasterDivisions, id=divisi_id)

    print_month = request.GET.get('print_month')

    if print_month:
        items = absensi_per_bulan.get(print_month, [])

        return render(request, 'admin/absen/print_absen.html', {
            'bulan_label': datetime.strptime(print_month, "%Y-%m").strftime("%B %Y"),
            'items': items,
            'title': f'Rekap Absensi Divisi {divisi.name}'
        })

    context = {
        'user': user,
        'divisi_id': divisi_id,
        'absensi_per_bulan': absensi_per_bulan,
        'bulan_labels': bulan_labels,
        'month_list': month_list,
        'year_list': year_list,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'title': f'Absen Divisi {divisi.name}',
    }

    return render(request, 'admin/absen/list_absen.html', context)

@login_auth
@admin_required
@superadmin_required
def cuti_master(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    cuti_list = MasterLeaves.objects.all()

    context = {
        'user': user,
        'title': 'Cuti Master',
        'cuti_list': cuti_list,
    }

    return render(request, 'admin/cuti_master/index.html', context)

@login_auth
@admin_required
@superadmin_required
def addCuti(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      name = request.POST['cuti_name']
      default_quota = request.POST['jatah']
      auto_days = request.POST['jmlh_hari']

      cuti = MasterLeaves(
          name=name,
          default_quota=default_quota,
          auto_days=auto_days,
      )
      cuti.save()

      messages.success(request, 'Data cuti berhasil diupload.')
      return redirect('/admins/cuti_master')
    
    context = {
      'user': user,
      'title': 'Tambah Cuti',
    }
    return render(request, 'admin/cuti_master/addForm.html', context)

@login_auth
@admin_required
@superadmin_required
def editCuti(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      name = request.POST['cuti_name']
      default_quota = request.POST['jatah']
      auto_days = request.POST['jmlh_hari']

      try:
        cuti = get_object_or_404(MasterLeaves, id=id)

        cuti.name = name
        cuti.default_quota = default_quota
        cuti.auto_days = auto_days
        cuti.save()

        messages.success(request, 'Data cuti berhasil diupdate.')
        return redirect('/admins/cuti_master')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data cuti: {e}')
        return redirect('/admins/cuti_master')
    
    cuti = get_object_or_404(MasterLeaves, id=id)

    context = {
      'user': user,
      'title': 'Edit Cuti',
      'cuti': cuti,
    }
    return render(request, 'admin/cuti_master/editForm.html', context)

@login_auth
@admin_required
@superadmin_required
def deleteCuti(request, id):
    try:
      cuti = get_object_or_404(MasterLeaves, id=id)
      cuti.delete()

      messages.success(request, 'Data cuti berhasil dihapus.')
      return redirect('/admins/cuti_master')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data cuti: {e}')
      return redirect('/admins/cuti_master')


@login_auth
@admin_required
def persetujuan_cuti(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    from django.utils.timezone import now
    current_year = now().year

    if user.is_admin == 1:
        status_filter = 'Pending'
        status_exclude = ['Pending']
        base_filter = {'nik__divisi': user.divisi}

    elif user.is_admin == 2:
        status_filter = 'Divisi Approved'
        status_exclude = ['Pending', 'Divisi Approved']
        base_filter = {}

    pengajuan_list = LeaveRequests.objects.filter(
        status=status_filter,
        created_at__year=current_year,
        **base_filter
    )

    approve_list = LeaveRequests.objects.exclude(
        status__in=status_exclude
    ).filter(
        created_at__year=current_year,
        **base_filter
    )

    context = {
        'user': user,
        'pengajuan_list': pengajuan_list,
        'approval_list': approve_list,
        'title': 'List Pengajuan Cuti Karyawan'
    }
    return render(request, 'admin/cuti_persetujuan/index.html', context)


@login_auth
@admin_required
def detail_pengajuan(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    pengajuan = get_object_or_404(LeaveRequests, id=id)

    if request.method == 'POST':
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        status = request.POST['status']
        note = request.POST['note']

        try:
            pengajuan = get_object_or_404(LeaveRequests, id=id)
            
            if user.is_admin == 1 and status == 'Approved':
                status = 'Divisi Approved'

            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.status = status
            pengajuan.note = note

            pengajuan.save()

            if user.is_admin == 2 and status == "Approved":
                from datetime import datetime, timedelta
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()

                cuti_schedule, created = MasterSchedules.objects.get_or_create(
                    id="CUTI",
                    defaults={
                        "name": "Cuti",
                        "start_time": "00:00",
                        "end_time": "00:00",
                    }
                )

                current = start
                while current <= end:

                    sudah_ada_absen = InAbsences.objects.filter(
                        nik=pengajuan.nik,
                        date_in__date=current
                    ).exists()

                    if not sudah_ada_absen:
                        InAbsences.objects.create(
                            nik=pengajuan.nik,
                            date_in=datetime.combine(current, datetime.min.time()),
                            status_in="Cuti",
                            date_out=datetime.combine(current, datetime.max.time()),
                            status_out="Cuti",
                            schedule=cuti_schedule
                        )
                    else:
                        absence = get_object_or_404(InAbsences, nik=pengajuan.nik, date_in__date=current)
                        try:
                            absence.status_in="Cuti"
                            absence.status_out="Cuti"
                            absence.schedule = cuti_schedule
                            absence.save()
                        except Exception as e:
                            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
                            return redirect('persetujuan_cuti')

                    sudah_ada_schedule = MappingSchedules.objects.filter(
                        nik=pengajuan.nik,
                        date=current
                    ).exists()

                    if not sudah_ada_schedule:
                        MappingSchedules.objects.create(
                            id=f"{pengajuan.nik.nik}_{current}",
                            nik=pengajuan.nik,
                            schedule=cuti_schedule,
                            date=current
                        )
                    else:
                        schedule = get_object_or_404(MappingSchedules, nik=pengajuan.nik, date=current)
                        try:
                            schedule.schedule = cuti_schedule
                            schedule.save()
                        except Exception as e:
                            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
                            return redirect('persetujuan_cuti')

                    current += timedelta(days=1)

            messages.success(request, 'Data persetujuan cuti berhasil disimpan.')
            return redirect('persetujuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
            return redirect('persetujuan_cuti')

    status = ['Pending', 'Approved', 'Rejected'] if user.is_admin == 1 else ['Divisi Approved', 'Approved', 'Rejected']
    context = {
       'user': user,
       'pengajuan': pengajuan,
       'title': 'Detail Pengajuan Cuti Karyawan',
       'status': status
    }

    return render(request, 'admin/cuti_persetujuan/detail.html', context)

@login_auth
@superadmin_required
def karyawan(request):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    query = request.GET.get('q', '').strip()

    all_users = Users.objects.all().order_by('nik')

    if query:
        all_users = all_users.filter(
            Q(nik__icontains=query) |
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(divisi__icontains=query)
        )

    paginator = Paginator(all_users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    divisi_ids = set(u.divisi for u in page_obj.object_list if u.divisi)

    divisions_map = {
        div.id: div
        for div in MasterDivisions.objects.filter(id__in=divisi_ids)
    }

    for u in page_obj.object_list:
        u.divisi = divisions_map.get(u.divisi, None)

    context = {
        'user': user,
        'page_obj': page_obj,
        'title': 'Daftar Karyawan',
        'query': query,
    }

    return render(request, 'admin/users/index.html', context)

@login_auth
@superadmin_required
def detail_karyawan(request, nik):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    user_detail = get_object_or_404(Users, nik=nik)

    division_detail = None
    
    if user_detail.divisi:
        try:
            division_detail = MasterDivisions.objects.get(id=user_detail.divisi)
        except MasterDivisions.DoesNotExist:
            division_detail = None
    
    context = {
        'user': user,
        'user_detail': user_detail,
        'division_detail': division_detail, 
        'title': 'Profile ' + user_detail.name
    }

    return render(request, 'admin/users/detail.html', context)

@login_auth
@superadmin_required
def editKaryawan(request, nik):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    detail_user = get_object_or_404(Users, nik=nik)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        divisi = request.POST.get('divisi')
        
        is_admin_input = request.POST.get('is_admin')
        is_admin = 1 if is_admin_input == 'on' else 0

        is_admin = 2 if detail_user.is_admin == 2 else is_admin
        
        try:
            detail_user.name = name
            detail_user.email = email
            detail_user.divisi = divisi
            detail_user.is_admin = is_admin

            detail_user.save()

            messages.success(request, 'Data Karyawan berhasil diupdate.')
            return redirect('karyawan')
        
        except Exception as e:
            messages.error(request, f'Gagal mengupdate data Karyawan: {e}')
            
            return redirect('editKaryawan', nik=detail_user.nik) 

    all_divisions = MasterDivisions.objects.all()

    division_detail = None
    if detail_user.divisi:
        try:
            division_detail = MasterDivisions.objects.get(name=detail_user.divisi)
        except MasterDivisions.DoesNotExist:
            pass

    context = {
        'user': user,
        'detail_user': detail_user,
        'all_divisions': all_divisions,
        'division_detail': division_detail,
        'title': 'Edit data ' + detail_user.name
    }

    return render(request, 'admin/users/editForm.html', context)

@login_auth
@superadmin_required
def deleteKaryawan(request, nik):
    try:
      user = get_object_or_404(Users, nik=nik)
      user.delete()

      messages.success(request, 'Data karyawan berhasil dihapus.')
      return redirect('karyawan')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data karyawan: {e}')
      return redirect('karyawan')
    






    