from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect , get_object_or_404
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.cache import cache
from django.contrib import messages
from django.utils import timezone
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
    return render(request, 'admin/403.html', status=403)

def err404(request, exception, template_name='admin/404.html'):
    return render(request, template_name, status=404)

@login_auth 
@admin_required
@superadmin_required
def dashboard(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    today = timezone.now().date()

    total_karyawan = Users.objects.count()

    total_jadwal = MappingSchedules.objects.filter(date=today).count()

    hadir_hari_ini = InAbsences.objects.filter(
        date_in__date=today
    ).count()

    belum_hadir = total_jadwal - hadir_hari_ini

    tepat_waktu_hari_ini = InAbsences.objects.filter(
        date_in__date=today,
        status_in="Tepat Waktu"
    ).count()

    terlamabt_hari_ini = InAbsences.objects.filter(
        date_in__date=today,
        status_in="Terlambat"
    ).count()
    
    cuti_hari_ini = InAbsences.objects.filter(
        date_in__date=today,
        status_in="Cuti"
    ).count()
    
    libur_hari_ini = InAbsences.objects.filter(
        date_in__date=today,
        status_in="Libur"
    ).count()

    # Grafik 7 hari
    labels_7_hari = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    data_7_hari = []

    for i in range(7):
        tanggal = today - timezone.timedelta(days=i)
        jumlah = InAbsences.objects.filter(date_in__date=tanggal).count()
        data_7_hari.append(jumlah)

    data_7_hari.reverse()

    from django.db.models import OuterRef, Subquery

    # Tabel presensi hari ini
    absence_subquery = (
        InAbsences.objects
        .filter(nik=OuterRef("nik"), date_in__date=today)
        .values("status_in")[:1]
    )

    presensi_hari_ini = (
        MappingSchedules.objects
        .select_related("nik", "schedule")
        .annotate(status_masuk=Subquery(absence_subquery))
        .filter(date=today)
        .order_by("nik__name")
    )

    context = {
        'user': user,
        'title': 'Dahsboard Admin',
        "total_jadwal": total_jadwal,
        "tepat_waktu_hari_ini": tepat_waktu_hari_ini,
        "terlamabt_hari_ini": terlamabt_hari_ini,
        "cuti_hari_ini": cuti_hari_ini,
        "libur_hari_ini": libur_hari_ini,
        "total_karyawan": total_karyawan,
        "hadir_hari_ini": hadir_hari_ini,
        "belum_hadir": belum_hadir,
        "labels_7_hari": labels_7_hari,
        "data_7_hari": data_7_hari,
        "presensi_hari_ini": presensi_hari_ini,
    }

    return render(request, "admin/dashboard.html", context)

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
              return redirect('/admins/divisi/add')

      # Create new data entry
      divisi = MasterDivisions(
          id=divisi_id,
          name=divisi_name,
      )
      divisi.save()

      messages.success(request, 'Data divisi berhasil diupload.')
      return redirect('/admins/divisi')
    
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
        return redirect('/admins/divisi')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data divisi: {e}')
        return redirect('/admins/divisi')
    
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
      return redirect('/admins/divisi')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data divisi: {e}')
      return redirect('/admins/divisi')
    
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
      return redirect('/admins/jadwal')
    
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
        return redirect('/admins/jadwal')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data jadwal: {e}')
        return redirect('/admins/jadwal')
    
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
      return redirect('/admins/jadwal')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data jadwal: {e}')
      return redirect('/admins/jadwal')
    
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
                    # messages.error(request, 'Wajah tidak terdeteksi dalam foto. Pendaftaran dibatalkan.')
                    # return redirect('/admins/addUser')
                    return JsonResponse({'status': 'error', 'message': 'Wajah tidak terdeteksi dalam foto. Pendaftaran dibatalkan.' })
                
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

                cache.delete("known_face_encodings")
                cache.delete("known_face_users")

                return JsonResponse({'status': 'success', 'message': 'Data karyawan berhasil diupload dan encoding wajah disimpan.'})
            
            except Exception as e:
                print(f"Error detail: {e}") 
                return JsonResponse({'status': 'error', 'message': 'Gagal mengupload data karyawan atau menghitung encoding: {e}' })
                
        else:
            return JsonResponse({ 'status': 'error', 'message': 'Foto tidak tersedia atau tidak valid.' })
    
    divisi_list = MasterDivisions.objects.all()
    context = {
      'divisi_list': divisi_list
    }
    return render(request, 'admin/addUser.html', context)

@login_auth
@admin_required
def mapping_jadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    # divisi_list = MasterDivisions.objects.filter(id=user.divisi)

    # if user.is_admin == 2:
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
                "days": {d: [] for d in range(1, total_hari + 1)}
            })

            if jadwal.schedule and jadwal.schedule.id != "CUTI" and jadwal.schedule.id != "LIBUR":
                jam = f"{jadwal.schedule.start_time.strftime('%H:%M')} - {jadwal.schedule.end_time.strftime('%H:%M')}"
            elif jadwal.schedule:
                jam = jadwal.schedule.name
            else:
                jam = "-"

            hasil[divisi.id][tahun][bulan_text][nik]["days"][hari].append(
                jam
            )

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
    if request.method != "POST":
        return redirect('/admins/mapping_jadwal')

    from datetime import datetime, time
    from django.utils import timezone
    import calendar
    from django.contrib import messages

    bulan = int(request.POST['bulan'])
    tahun = int(request.POST['tahun'])

    _, jumlah_hari = calendar.monthrange(tahun, bulan)
    tanggal_list = list(range(1, jumlah_hari + 1))

    users = Users.objects.all()

    for user in users:
        for tgl in tanggal_list:
            date_str = f"{tahun}-{bulan:02d}-{tgl:02d}"

            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            local_datetime = timezone.make_aware(
                datetime.combine(date_obj.date(), time(0, 0))
            )

            for shift_order in [1, 2]:
                shift_key = f'shift_{user.nik}_{tgl}_{shift_order}'
                shift_id = request.POST.get(shift_key)

                if not shift_id:
                    continue

                shift = MasterSchedules.objects.filter(id=shift_id).first()
                if not shift:
                    continue

                if shift.name.lower() == 'libur':
                    if not InAbsences.objects.filter(
                        nik=user,
                        date_in__date=local_datetime.date(),
                        status_in="Libur"
                    ).exists():
                        from datetime import time

                        safe_datetime = timezone.make_aware(
                            datetime.combine(date_obj.date(), time(12, 0))
                        )

                        InAbsences.objects.create(
                            nik=user,
                            date_in=safe_datetime,
                            date_out=safe_datetime,
                            status_in="Libur",
                            status_out="Libur",
                            schedule=shift
                        )

                mapping_id = f"{user.nik}_{date_str}_{shift_order}"

                mapping, created = MappingSchedules.objects.get_or_create(
                    id=mapping_id,
                    nik=user,
                    date=local_datetime.date(),
                    shift_order=shift_order,
                    defaults={'schedule': shift}
                )

                if not created:
                    mapping.schedule = shift
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
        shift_order = item.shift_order
        schedule_id = item.schedule.id

        jadwal.setdefault(nik, {})
        jadwal[nik].setdefault(hari, {})
        jadwal[nik][hari][shift_order] = schedule_id

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
    if request.method != "POST":
        return redirect('/admins/mapping_jadwal')

    import calendar
    from datetime import date, datetime, time
    from django.utils import timezone
    from django.contrib import messages

    bulan = int(request.POST['bulan'])
    tahun = int(request.POST['tahun'])

    _, jumlah_hari = calendar.monthrange(tahun, bulan)
    tanggal_list = range(1, jumlah_hari + 1)

    users = Users.objects.all()

    for user in users:
        for tgl in tanggal_list:
            local_date = date(tahun, bulan, tgl)

            safe_datetime = timezone.make_aware(
                datetime.combine(local_date, time(12, 0))
            )

            for shift_order in [1, 2]:
                shift_key = f"shift_{user.nik}_{tgl}_{shift_order}"
                shift_id = request.POST.get(shift_key)

                mapping = MappingSchedules.objects.filter(
                    nik=user,
                    date=local_date,
                    shift_order=shift_order
                ).first()

                if shift_id:
                    shift = MasterSchedules.objects.filter(id=shift_id).first()
                    if not shift:
                        continue

                    if shift.name.upper() == "LIBUR":
                        InAbsences.objects.get_or_create(
                            nik=user,
                            date_in__date=local_date,
                            defaults={
                                "date_in": safe_datetime,
                                "date_out": safe_datetime,
                                "status_in": "Libur",
                                "status_out": "Libur",
                                "schedule": shift
                            }
                        )

                    # ========= UPDATE / CREATE MAPPING =========
                    if mapping:
                        mapping.schedule = shift
                        mapping.save()
                    else:
                        MappingSchedules.objects.create(
                            id=f"{user.nik}_{local_date}_{shift_order}",
                            nik=user,
                            date=local_date,
                            shift_order=shift_order,
                            schedule=shift
                        )

                # ===============================
                # JIKA SHIFT DIKOSONGKAN
                # ===============================
                else:
                    if mapping:
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

    print_month = request.GET.get('print_month')
    print_range = request.GET.get('print_range')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    is_range_filter = bool(start_date and end_date)

    list_absen = (
        InAbsences.objects
        .filter(nik__divisi=divisi_id)
        .select_related('nik', 'schedule')
        .order_by('nik', 'date_in')
    )

    from datetime import datetime

    if print_range and start_date and end_date:
        start = timezone.make_aware(
            datetime.strptime(start_date, "%Y-%m-%d")
        )
        end = timezone.make_aware(
            datetime.strptime(end_date, "%Y-%m-%d")
        ).replace(hour=23, minute=59, second=59)

        items = list_absen.filter(date_in__range=(start, end))

        for absen in items:
            _hitung_absen(absen)

        divisi = get_object_or_404(MasterDivisions, id=divisi_id)

        return render(request, 'admin/absen/print_absen.html', {
            'bulan_label': f'Periode {start_date} s/d {end_date}',
            'items': items,
            'title': f'Rekap Absensi Divisi {divisi.name}'
        })

    if print_month:
        absensi_per_bulan = {}

        for absen in list_absen:
            _hitung_absen(absen)
            key = absen.date_in.strftime("%Y-%m")
            absensi_per_bulan.setdefault(key, []).append(absen)

        items = absensi_per_bulan.get(print_month, [])

        divisi = get_object_or_404(MasterDivisions, id=divisi_id)

        return render(request, 'admin/absen/print_absen.html', {
            'bulan_label': datetime.strptime(print_month, "%Y-%m").strftime("%B %Y"),
            'items': items,
            'title': f'Rekap Absensi Divisi {divisi.name}'
        })

    if is_range_filter:
        start = timezone.make_aware(
            datetime.strptime(start_date, "%Y-%m-%d")
        )
        end = timezone.make_aware(
            datetime.strptime(end_date, "%Y-%m-%d")
        ).replace(hour=23, minute=59, second=59)

        list_absen = list_absen.filter(date_in__range=(start, end))

        for absen in list_absen:
            _hitung_absen(absen)

        divisi = get_object_or_404(MasterDivisions, id=divisi_id)

        return render(request, 'admin/absen/list_absen.html', {
            'user': user,
            'divisi_id': divisi_id,
            'is_range_filter': True,
            'list_absen': list_absen,
            'start_date': start_date,
            'end_date': end_date,
            'title': f'Absen Divisi {divisi.name}',
        })

    absensi_per_bulan = {}

    for absen in list_absen:
        _hitung_absen(absen)
        key = absen.date_in.strftime("%Y-%m")
        absensi_per_bulan.setdefault(key, []).append(absen)

    absensi_per_bulan = dict(sorted(
        absensi_per_bulan.items(),
        reverse=True
    )[:6])

    bulan_labels = {
        k: datetime.strptime(k, "%Y-%m").strftime("%B %Y")
        for k in absensi_per_bulan
    }

    divisi = get_object_or_404(MasterDivisions, id=divisi_id)

    return render(request, 'admin/absen/list_absen.html', {
        'user': user,
        'divisi_id': divisi_id,
        'is_range_filter': False,
        'absensi_per_bulan': absensi_per_bulan,
        'bulan_labels': bulan_labels,
        'title': f'Absen Divisi {divisi.name}',
    })

def _hitung_absen(absen):
    from datetime import datetime, timedelta

    absen.late_minutes = 0
    absen.late_time = None
    absen.total_work_minutes = 0
    absen.total_work = None

    if absen.schedule and absen.schedule.id in ('CUTI', 'LIBUR'):
        absen.total_work = "00:00:00"
        absen.total_work_minutes = 0
        return

    if absen.schedule and absen.schedule.start_time:
        shift_start = timezone.make_aware(
            datetime.combine(absen.date_in.date(), absen.schedule.start_time)
        )

        diff = (absen.date_in - shift_start).total_seconds()
        if diff > 0:
            absen.late_minutes = int(diff // 60)
            absen.late_time = str(timedelta(minutes=absen.late_minutes))

    if absen.date_out:
        start_work = absen.date_in
        end_work = absen.date_out

        if absen.schedule and absen.schedule.start_time and absen.schedule.end_time:
            shift_start_time = absen.schedule.start_time
            shift_end_time = absen.schedule.end_time

            if shift_end_time < shift_start_time:
                if end_work <= start_work:
                    end_work += timedelta(days=1)

        total_seconds = (end_work - start_work).total_seconds()
        if total_seconds > 0:
            absen.total_work_minutes = int(total_seconds // 60)
            absen.total_work = str(timedelta(minutes=absen.total_work_minutes))

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
      return redirect('/admins/cuti')
    
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
        return redirect('/admins/cuti')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data cuti: {e}')
        return redirect('/admins/cuti')
    
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
      return redirect('/admins/cuti')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data cuti: {e}')
      return redirect('/admins/cuti')


@login_auth
@admin_required
def persetujuan_cuti(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    from django.utils.timezone import now
    current_year = now().year

    if user.is_admin == 1:
        status_filter = 'Pending'
        status_exclude = ['Pending']
        base_filter = {'user_target': user}

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
                        "end_time": "00:00"
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
                            schedule=cuti_schedule,
                            shift_order=1
                        )
                    else:
                        absence = get_object_or_404(InAbsences, nik=pengajuan.nik, date_in__date=current)
                        try:
                            absence.status_in="Cuti"
                            absence.status_out="Cuti"
                            absence.schedule = cuti_schedule
                            absence.shift_order= 1
                            absence.save()
                        except Exception as e:
                            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
                            return redirect('/admins/persetujuan_cuti')

                    sudah_ada_schedule = MappingSchedules.objects.filter(
                        nik=pengajuan.nik,
                        date=current
                    ).exists()

                    if not sudah_ada_schedule:
                        MappingSchedules.objects.create(
                            id=f"{pengajuan.nik.nik}_{current}",
                            nik=pengajuan.nik,
                            schedule=cuti_schedule,
                            date=current,
                            shift_order=1
                        )
                    else:
                        schedule = get_object_or_404(MappingSchedules, nik=pengajuan.nik, date=current)
                        try:
                            schedule.schedule = cuti_schedule
                            schedule.save()
                        except Exception as e:
                            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
                            return redirect('/admins/persetujuan_cuti')

                    current += timedelta(days=1)

            messages.success(request, 'Data persetujuan cuti berhasil disimpan.')
            return redirect('/admins/persetujuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}')
            return redirect('/admins/persetujuan_cuti')

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
            return redirect('/admins/karyawan')
        
        except Exception as e:
            messages.error(request, f'Gagal mengupdate data Karyawan: {e}')
            
            return redirect('/admins/karyawan/edit', nik=detail_user.nik) 

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
      return redirect('/admins/karyawan')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data karyawan: {e}')
      return redirect('/admins/karyawan')
    






    