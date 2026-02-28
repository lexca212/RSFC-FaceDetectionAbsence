from core.utils.send_telegram_message import send_telegram_message, send_telegram_message_hrd
from .services.permission_service import apply_permission, revert_permission
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect , get_object_or_404
from .services.leave_service import apply_leave, revert_leave
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

def request_reset_password(request):
    from django.template.loader import render_to_string
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from datetime import timedelta
    import secrets

    if request.method == 'POST':
        email = request.POST.get('email')

        user = Users.objects.filter(email=email).first()
        if not user:
            return redirect('reset_password_done')

        token = secrets.token_urlsafe(32)

        PasswordResetToken.objects.create(
            user=user,
            token=token,
            expired_at=timezone.now() + timedelta(minutes=30)
        )

        reset_link = request.build_absolute_uri(
            f'/admins/reset-password/{token}/'
        )

        # Render HTML
        html_content = render_to_string(
            'email/reset_password.html',
            {
                'user': user,
                'reset_link': reset_link
            }
        )

        # Plain text fallback (WAJIB)
        text_content = f"""
Halo {user.name},

Klik link berikut untuk reset password:
{reset_link}

Link berlaku 30 menit.
"""

        email_message = EmailMultiAlternatives(
            subject='Reset Password Akun Anda',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )

        email_message.attach_alternative(html_content, "text/html")
        email_message.send()
    
        return redirect('reset_password_done')

    return render(request, 'admin/lupa_password/formPermintaan.html')

def confirm_reset_password(request, token):
    reset_token = PasswordResetToken.objects.filter(token=token).first()

    if not reset_token or not reset_token.is_valid():
        messages.error(request, 'Link reset tidak valid atau kadaluarsa')
        return redirect('reset_password')

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Password tidak sama')
            return redirect(request.path)

        user = reset_token.user
        user.password = make_password(password1)
        user.save()

        reset_token.is_used = True
        reset_token.save()

        messages.success(request, 'Password berhasil diubah')
        return redirect('login')

    return render(request, 'admin/lupa_password/reset_confirm.html')

def err403(request):
    return render(request, 'admin/403.html', status=403)

def err404(request, exception, template_name='admin/404.html'):
    return render(request, template_name, status=404)

def dekstop_only403(request):
    return render(request, 'admin/dekstop_only403.html', status=403)

@login_auth 
@admin_required
@superadmin_required
def dashboard(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    from datetime import datetime, time
    
    today = timezone.now().date()

    start = timezone.make_aware(
        datetime.combine(today, time.min)
    )

    end = timezone.make_aware(
        datetime.combine(today, time.max)
    )

    filter_status = request.GET.get("status")

    total_karyawan = Users.objects.count()

    total_jadwal = MappingSchedules.objects.filter(date=today).count()

    hadir_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in__in=["Tepat Waktu", "Terlambat"]
    ).count()

    tepat_waktu_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in="Tepat Waktu"
    ).count()

    terlamabt_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in="Terlambat"
    ).count()
    
    cuti_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in="Cuti"
    ).count()
    
    libur_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in="Libur"
    ).count()

    izin_hari_ini = InAbsences.objects.filter(
        date_in__range=(start, end),
        status_in="Izin"
    ).count()

    belum_hadir = total_jadwal - hadir_hari_ini - libur_hari_ini

    # Grafik 7 hari
    labels_7_hari = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
    data_7_hari = []

    for i in range(7):
        tanggal = today - timezone.timedelta(days=i)
        jumlah = InAbsences.objects.filter(date_in__date=tanggal).count()
        data_7_hari.append(jumlah)

    data_7_hari.reverse()

    from django.db.models import OuterRef, Subquery, DateTimeField

    # Tabel presensi hari ini
    absence_qs = (
        InAbsences.objects
        .filter(
            nik=OuterRef("nik"),
            schedule=OuterRef("schedule"),
            date_in__range=(start, end)
        )
        .order_by("date_in")
    )

    status_subquery = absence_qs.values("status_in")[:1]

    jam_masuk_subquery = absence_qs.values("date_in")[:1]

    presensi_hari_ini = (
        MappingSchedules.objects
        .select_related("nik", "schedule")
        .annotate(
            status_masuk=Subquery(status_subquery),
            jam_masuk=Subquery(
                jam_masuk_subquery,
                output_field=DateTimeField()
            )
        )
        .filter(date=today)
    )

    if filter_status:
        if filter_status == "Belum Hadir":
            presensi_hari_ini = presensi_hari_ini.filter(status_masuk__isnull=True)
        elif filter_status == "Hadir":
            presensi_hari_ini = presensi_hari_ini.filter(status_masuk__isnull=False)
        elif filter_status == "Semua":
            presensi_hari_ini = presensi_hari_ini.all()
        else:
            presensi_hari_ini = presensi_hari_ini.filter(status_masuk=filter_status)

    presensi_hari_ini = presensi_hari_ini.order_by("nik__name")

    context = {
        'user': user,
        'title': 'Dahsboard Admin',
        "total_jadwal": total_jadwal,
        "tepat_waktu_hari_ini": tepat_waktu_hari_ini,
        "terlamabt_hari_ini": terlamabt_hari_ini,
        "cuti_hari_ini": cuti_hari_ini,
        "libur_hari_ini": libur_hari_ini,
        "izin_hari_ini": izin_hari_ini,
        "total_karyawan": total_karyawan,
        "hadir_hari_ini": hadir_hari_ini,
        "belum_hadir": belum_hadir,
        "labels_7_hari": labels_7_hari,
        "data_7_hari": data_7_hari,
        "presensi_hari_ini": presensi_hari_ini,
        "filter_status": filter_status
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
def editJadwal(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      jadwal_id = request.POST['jadwal_id']
      jadwal_name = request.POST['jadwal_name']
      start_time = request.POST['jam_masuk']
      end_time = request.POST['jam_keluar']

      try:
        jadwal = get_object_or_404(MasterSchedules, id=jadwal_id)

        if id == 'CUTI' or id == 'LIBUR' or id == 'IZIN':
          messages.error(request, 'Jadwal ini tidak dapat dihapus.')
          return redirect('/admins/jadwal')

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

      if id == 'CUTI' or id == 'LIBUR' or id == 'IZIN':
          messages.error(request, 'Jadwal ini tidak dapat dihapus.')
          return redirect('/admins/jadwal')
      
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
@superadmin_required
def update_encode(request, nik):
    user = get_object_or_404(Users, nik=nik)

    if request.method == 'POST':
        photo_data = request.POST.get('photo', '')

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
                    return JsonResponse({'status': 'error', 'message': 'Wajah tidak terdeteksi dalam foto. Pendaftaran dibatalkan.' })
                
                face_enc = encodings[0] 
                
                serialized_encoding = pickle.dumps(face_enc)
                
                user.photo=photo_file
                user.face_encoding=serialized_encoding
                user.save()

                cache.delete("known_face_encodings")
                cache.delete("known_face_users")

                return JsonResponse({'status': 'success', 'message': 'Data karyawan berhasil diupload dan encoding wajah disimpan.'})
            
            except Exception as e:
                print(f"Error detail: {e}") 
                return JsonResponse({'status': 'error', 'message': 'Gagal mengupload data karyawan atau menghitung encoding: {e}' })
                
        else:
            return JsonResponse({ 'status': 'error', 'message': 'Foto tidak tersedia atau tidak valid.' })
    
    context = {
        'user': user
    }
    return render(request, 'admin/users/updateEncode.html', context)

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

            if jadwal.schedule and jadwal.schedule.id != "CUTI" and jadwal.schedule.id != "LIBUR" and jadwal.schedule.id != "IZIN":
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

    schedules = MasterSchedules.objects.exclude(id__in=['CUTI', 'IZIN']).all()

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
                        from datetime import time, date

                        local_date = date(tahun, bulan, tgl)

                        safe_datetime = timezone.make_aware(
                            datetime.combine(date_obj.date(), time(12, 0))
                        )

                        InAbsences.objects.create(
                            nik=user,
                            date_in=safe_datetime,
                            date_out=safe_datetime,
                            status_in="Libur",
                            status_out="Libur",
                            schedule=shift,
                            date=local_date,
                            shift_order=shift_order,
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
    from django.db import transaction
    from datetime import date, datetime, time

    if request.method != "POST":
        return redirect('/admins/mapping_jadwal')

    bulan = int(request.POST['bulan'])
    tahun = int(request.POST['tahun'])

    _, jumlah_hari = calendar.monthrange(tahun, bulan)
    tanggal_list = range(1, jumlah_hari + 1)

    users = list(Users.objects.all())

    # ===== PRELOAD SCHEDULE =====
    schedule_map = {
        str(s.id): s for s in MasterSchedules.objects.all()
    }

    # ===== PRELOAD MAPPING =====
    existing_mappings = MappingSchedules.objects.filter(
        date__year=tahun,
        date__month=bulan,
        nik__in=users
    )

    mapping_dict = {
        (m.nik_id, m.date, m.shift_order): m
        for m in existing_mappings
    }

    # ===== PRELOAD LIBUR ABSENCE =====
    existing_absences = InAbsences.objects.filter(
        date__year=tahun,
        date__month=bulan,
        nik__in=users
    )

    absence_dict = {
        (a.nik_id, a.date, a.shift_order): a
        for a in existing_absences
    }

    to_create_mapping = []
    to_update_mapping = []
    to_delete_mapping = []

    to_create_absence = []
    to_update_absence = []

    try:
        with transaction.atomic():

            for user in users:
                for tgl in tanggal_list:

                    local_date = date(tahun, bulan, tgl)

                    # hanya shift 1 (real case kamu)
                    shift_order = 1

                    shift_key = f"shift_{user.nik}_{tgl}_{shift_order}"
                    shift_id = request.POST.get(shift_key)

                    mapping_key = (user.nik, local_date, shift_order)
                    mapping = mapping_dict.get(mapping_key)

                    if not shift_id or shift_id == "-":
                        if mapping:
                            to_delete_mapping.append(mapping)
                        continue

                    shift = schedule_map.get(shift_id)
                    if not shift:
                        continue

                    # ===== HANDLE LIBUR =====
                    if shift.name.upper() == "LIBUR":

                        safe_datetime = timezone.make_aware(
                            datetime.combine(local_date, time(12, 0))
                        )

                        absence = absence_dict.get(mapping_key)

                        if absence:
                            absence.date_in = safe_datetime
                            absence.date_out = safe_datetime
                            absence.status_in = "Libur"
                            absence.status_out = "Libur"
                            absence.schedule = shift
                            to_update_absence.append(absence)
                        else:
                            to_create_absence.append(
                                InAbsences(
                                    nik=user,
                                    date=local_date,
                                    shift_order=shift_order,
                                    date_in=safe_datetime,
                                    date_out=safe_datetime,
                                    status_in="Libur",
                                    status_out="Libur",
                                    schedule=shift,
                                )
                            )
                    
                    if shift.name.upper() == "-":
                            mapping.delete()

                    # ===== HANDLE MAPPING =====
                    if mapping:
                        if mapping.schedule_id != shift.id:
                            mapping.schedule = shift
                            to_update_mapping.append(mapping)
                    else:
                        to_create_mapping.append(
                            MappingSchedules(
                                id=f"{user.nik}_{local_date}_{shift_order}",
                                nik=user,
                                date=local_date,
                                shift_order=shift_order,
                                schedule=shift
                            )
                        )

            # ===== EXECUTE BULK OPS =====

            if to_delete_mapping:
                MappingSchedules.objects.filter(
                    id__in=[m.id for m in to_delete_mapping]
                ).delete()

            if to_create_mapping:
                MappingSchedules.objects.bulk_create(
                    to_create_mapping,
                    batch_size=500
                )

            if to_update_mapping:
                MappingSchedules.objects.bulk_update(
                    to_update_mapping,
                    ['schedule'],
                    batch_size=500
                )

            if to_create_absence:
                InAbsences.objects.bulk_create(
                    to_create_absence,
                    batch_size=500
                )

            if to_update_absence:
                InAbsences.objects.bulk_update(
                    to_update_absence,
                    ['date_in', 'date_out', 'status_in', 'status_out', 'schedule'],
                    batch_size=500
                )

    except Exception as e:
        messages.error(request, f"Gagal update jadwal: {e}")
        return redirect('/admins/mapping_jadwal')

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
    import pytz
    
    tz_jakarta = pytz.timezone('Asia/Jakarta')
    local_date_in = absen.date_in.astimezone(tz_jakarta)
    
    absen.late_minutes = 0
    absen.late_time = "00:00:00"
    absen.total_work_minutes = 0
    absen.total_work = "00:00:00"

    if absen.schedule and absen.schedule.id in ('LIBUR', 'CUTI', 'IZIN') or \
       getattr(absen, 'status_in', '').lower() == 'libur':
        return 

    if absen.schedule and absen.schedule.start_time:
        naive_shift_start = datetime.combine(local_date_in.date(), absen.schedule.start_time)
        shift_start = tz_jakarta.localize(naive_shift_start)

        diff_seconds = (local_date_in - shift_start).total_seconds()
        
        if diff_seconds > 0:
            absen.late_minutes = int(diff_seconds // 60)
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
        status_filter = ['Pending']
        status_exclude = ['Pending']
        base_filter = {'user_target': user}

    elif user.is_admin == 2:
        status_filter = ['Divisi Approved']
        status_exclude = ['Pending', 'Divisi Approved']
        base_filter = {}

    pengajuan_list = LeaveRequests.objects.filter(
        status__in=status_filter,
        **base_filter
    )

    approve_list = LeaveRequests.objects.exclude(
        status__in=status_exclude
    ).filter(
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
        new_status = request.POST['status']
        note = request.POST['note']

        try:
            old_status = pengajuan.status 

            if old_status == 'Approved' and new_status == "Cancelled" and user.is_admin != 2:
                messages.error(request, "Pembatalan cuti hanya dapat dilakukan oleh HRD.")
                return redirect('/admins/persetujuan_cuti')

            # === NORMALISASI STATUS ===
            if user.is_admin == 1 and new_status == 'Approved':
                new_status = 'Divisi Approved'

            from datetime import datetime

            start_date = datetime.strptime(
                request.POST['start_date'], "%Y-%m-%d"
            ).date()

            end_date = datetime.strptime(
                request.POST['end_date'], "%Y-%m-%d"
            ).date()

            # === UPDATE DATA ===
            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.status = new_status
            pengajuan.note = note
            pengajuan.save()

            if user.is_admin == 1 and  new_status == 'Divisi Approved':
                message = f"""
📢 <b>Pengajuan Cuti Baru</b>

Nama: {pengajuan.nik.name}
Jenis: {pengajuan.leave_type.name}
Tanggal: {start_date} s.d. {end_date}
Alasan: {pengajuan.reason}
PJ Unit: {pengajuan.user_target.name}

https://s.id/asidewa

Silakan klik tautan di atas dan pilih menu <b>Persetujuan Cuti</b> untuk melakukan approval.
            """
                hrd_list = Users.objects.filter(is_admin=2).exclude(telegram_chat_id=None)

                send_telegram_message_hrd(hrd_list, message)

            if user.is_admin == 2 and new_status != 'Divisi Approved' and pengajuan.nik.telegram_chat_id:
                message = f"""
📢 <b>Persetujuan Cuti</b>

Nama: {pengajuan.nik.name}
Jenis: {pengajuan.leave_type.name}
Tanggal: {start_date} s.d. {end_date}
Catatan: {note}
Status: <b>{new_status}</b>

Silakan check kesesuaian jadwal Anda, dengan hasil pengajuan ini.

<i>Hubungi Unit IT jika terdapat kesalahan.</i>
            """
                send_telegram_message(pengajuan.nik.telegram_chat_id, message)

            # === APPLY CUTI (HANYA SEKALI) ===
            if (
                user.is_admin == 2 and
                old_status != "Approved" and
                new_status == "Approved"
            ):
                apply_leave(pengajuan)

            # === REVERT CUTI ===
            if (
                old_status == "Approved" and
                new_status == "Cancelled"
            ):
                revert_leave(pengajuan)

            messages.success(request, 'Data persetujuan cuti berhasil disimpan.')
            return redirect('/admins/persetujuan_cuti')

        except Exception as e:
            messages.error(
                request,
                f'Gagal menyimpan data persetujuan pengajuan cuti. Error: {e}'
            )
            return redirect('/admins/persetujuan_cuti')

    # === STATUS OPTION UNTUK FORM ===
    if pengajuan.status == 'Approved':
        status_choices = ( ['Approved', 'Cancelled'] )
    else:
        status_choices = (
            ['Pending', 'Approved', 'Rejected',  'Cancelled']
            if user.is_admin == 1
            else ['Divisi Approved', 'Approved', 'Rejected', 'Cancelled']
        )
    

    context = {
        'user': user,
        'pengajuan': pengajuan,
        'title': 'Detail Pengajuan Cuti Karyawan',
        'status': status_choices
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
        telegram_chat_id = request.POST.get('telegram_chat_id')
        
        is_admin_input = request.POST.get('is_admin')
        is_admin = 1 if is_admin_input == 'on' else 0

        is_admin = 2 if detail_user.is_admin == 2 else is_admin
        
        try:
            detail_user.name = name
            detail_user.email = email
            detail_user.divisi = divisi
            detail_user.is_admin = is_admin
            detail_user.telegram_chat_id = telegram_chat_id

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
    
@login_auth
@admin_required
@superadmin_required
def izin_master(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    izin_list = MasterPermission.objects.all()

    context = {
        'user': user,
        'title': 'Izin Master',
        'izin_list': izin_list,
    }

    return render(request, 'admin/izin_master/index.html', context)

@login_auth
@admin_required
@superadmin_required
def addIzin(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      name = request.POST['izin_name']
      max_per_month = request.POST['jatah']
      max_days = request.POST['jmlh_hari']
      is_requires_attachment = request.POST['bukti']

      izin = MasterPermission(
        name=name,
        max_per_month=max_per_month,
        max_days=max_days,
        is_requires_attachment=is_requires_attachment,  
      )
      izin.save()

      messages.success(request, 'Data izin berhasil diupload.')
      return redirect('/admins/izin')
    
    context = {
      'user': user,
      'title': 'Tambah Izin',
    }
    return render(request, 'admin/izin_master/addForm.html', context)

@login_auth
@admin_required
@superadmin_required
def editIzin(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
      name = request.POST['izin_name']
      max_per_month = request.POST['jatah']
      max_days = request.POST['jmlh_hari']
      is_requires_attachment = request.POST['bukti']

      try:
        izin = get_object_or_404(MasterPermission, id=id)

        izin.name = name
        izin.max_per_month = max_per_month
        izin.max_days = max_days
        izin.is_requires_attachment = is_requires_attachment
        izin.save()

        messages.success(request, 'Data izin berhasil diupdate.')
        return redirect('/admins/izin')
      
      except Exception as e:
        messages.error(request, f'Gagal mengupdate data izin: {e}')
        return redirect('/admins/izin')
    
    izin = get_object_or_404(MasterPermission, id=id)

    context = {
      'user': user,
      'title': 'Edit Izin',
      'izin': izin,
    }
    return render(request, 'admin/izin_master/editForm.html', context)
 
@login_auth
@admin_required
@superadmin_required
def deleteIzin(request, id):
    try:
      izin = get_object_or_404(MasterPermission, id=id)
      izin.delete()

      messages.success(request, 'Data izin berhasil dihapus.')
      return redirect('/admins/izin')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data izin: {e}')
      return redirect('/admins/izin')

@login_auth
@admin_required
def persetujuan_izin(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    from datetime import date
    from django.utils.timezone import now

    today = now().date()

    start_range = today.replace(day=1)

    if today.month == 12:
        end_range = date(today.year + 1, 1, 31)
    else:
        end_range = date(today.year, today.month + 2, 1) - date.resolution

    if user.is_admin == 1:
        status_filter = ['Pending']
        status_exclude = ['Pending']
        base_filter = {'user_target': user}

    elif user.is_admin == 2:
        status_filter = ['Divisi Approved']
        status_exclude = ['Pending', 'Divisi Approved']
        base_filter = {}

    pengajuan_list = PermissionRequests.objects.filter(
        status__in=status_filter,
        start_date__range=(start_range, end_range),
        **base_filter
    )

    approve_list = PermissionRequests.objects.exclude(
        status__in=status_exclude
    ).filter(
        start_date__range=(start_range, end_range),
        **base_filter
    )

    context = {
        'user': user,
        'pengajuan_list': pengajuan_list,
        'approval_list': approve_list,
        'title': 'List Pengajuan Izin Karyawan'
    }

    return render(request, 'admin/izin_persetujuan/index.html', context)

@login_auth
@admin_required
def detail_pengajuan_izin(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    pengajuan = get_object_or_404(PermissionRequests, id=id)

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        new_status = request.POST.get('status')
        note = request.POST.get('note')

        try:
            old_status = pengajuan.status

            if old_status == 'Approved' and new_status == "Cancelled" and user.is_admin != 2:
                messages.error(request, "Pembatalan izin hanya dapat dilakukan oleh HRD.")
                return redirect('/admins/persetujuan_izin')

            # === NORMALISASI STATUS ===
            if user.is_admin == 1 and new_status == 'Approved':
                new_status = 'Divisi Approved'

            from datetime import datetime

            start_date = datetime.strptime(
                request.POST['start_date'], "%Y-%m-%d"
            ).date()

            end_date = datetime.strptime(
                request.POST['end_date'], "%Y-%m-%d"
            ).date()

            # === UPDATE DATA PENGAJUAN ===
            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.status = new_status
            pengajuan.note = note
            pengajuan.save()

            if user.is_admin == 1 and  new_status == 'Divisi Approved':
                message = f"""
📢 <b>Pengajuan Izin Baru</b>

Nama: {pengajuan.nik.name}
Jenis: {pengajuan.permission_type.name}
Tanggal: {start_date} s.d. {end_date}
Alasan: {pengajuan.reason}
PJ Unit: {pengajuan.user_target.name}

https://s.id/asidewa

Silakan klik tautan di atas dan pilih menu <b>Persetujuan Izin</b> untuk melakukan approval.
            """
                hrd_list = Users.objects.filter(is_admin=2).exclude(telegram_chat_id=None)

                send_telegram_message_hrd(hrd_list, message)

            if user.is_admin == 2 and new_status != 'Divisi Approved' and pengajuan.nik.telegram_chat_id:
                message = f"""
📢 <b>Persetujuan Izin</b>

Nama: {pengajuan.nik.name}
Jenis: {pengajuan.permission_type.name}
Tanggal: {start_date} s.d. {end_date}
Catatan: {note}
Status: <b>{new_status}</b>

Silakan check kesesuaian jadwal Anda, dengan hasil pengajuan ini.

<i>Hubungi Unit IT jika terdapat kesalahan.</i>
            """
                send_telegram_message(pengajuan.nik.telegram_chat_id, message)

            # === APPLY IZIN ===
            if user.is_admin == 2 and new_status == "Approved" and old_status != "Approved":
                apply_permission(pengajuan)

            # === CANCEL IZIN ===
            if (
                user.is_admin == 2
                and old_status == "Approved"
                and new_status == "Cancelled"
            ):
                revert_permission(pengajuan)

            messages.success(request, 'Data persetujuan izin berhasil disimpan.')
            return redirect('/admins/persetujuan_izin')

        except Exception as e:
            messages.error(
                request,
                f'Gagal menyimpan data persetujuan izin. Error: {e}'
            )
            return redirect('/admins/persetujuan_izin')

    if pengajuan.status == 'Approved':
        status_choices = ( ['Approved', 'Cancelled'] )
    else:
        status_choices = (
            ['Pending', 'Approved', 'Rejected',  'Cancelled']
            if user.is_admin == 1
            else ['Divisi Approved', 'Approved', 'Rejected', 'Cancelled']
        )

    context = {
        'user': user,
        'pengajuan': pengajuan,
        'title': 'Detail Pengajuan Izin Karyawan',
        'status': status_choices
    }

    return render(request, 'admin/izin_persetujuan/detail.html', context)

def timedelta_to_hms(td):
    if not td:
        return "00:00:00"

    total_seconds = int(td.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@login_auth
@admin_required
@superadmin_required
def riwayat_keluar (request):
    from datetime import datetime, timedelta
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    divisi = request.GET.get('divisi')
    start = request.GET.get('start')
    end = request.GET.get('end')

    qs = (
        OutPermission.objects
        .select_related('nik')
        .order_by('-time_out')
    )

    if divisi:
        qs = qs.filter(nik__divisi=divisi)

    out_active = qs.filter(status='Keluar')

    out_history = qs

    if start and end:
        start_dt = timezone.make_aware(
            datetime.strptime(start, "%Y-%m-%d")
        )
        end_dt = timezone.make_aware(
            datetime.strptime(end, "%Y-%m-%d")
        ).replace(hour=23, minute=59, second=59)

        out_history = out_history.filter(
            time_out__range=(start_dt, end_dt)
        )
    else:
        out_history = out_history.filter(
            time_out__gte=timezone.now() - timedelta(days=31)
        )

    for o in out_history:
        if o.time_out and o.time_in:
            delta = o.time_in - o.time_out
            o.duration_minutes = int(delta.total_seconds() // 60)
        elif o.status == 'Keluar':
            delta = timezone.now() - o.time_out
            o.duration_minutes = int(delta.total_seconds() // 60)
        else:
            o.duration_minutes = None

    divisi_list = (
        Users.objects
        .exclude(divisi__isnull=True)
        .exclude(divisi__exact='')
        .values_list('divisi', flat=True)
        .distinct()
        .order_by('divisi')
    )

    return render(request, 'admin/keluar/index.html', {
        'user': user,
        'title': 'Rekap Izin Keluar (Out Permission)',

        'divisi_list': divisi_list,

        'out_active': out_active,
        'out_history': out_history,

        'selected_divisi': divisi,
        'start_date': start,
        'end_date': end,
    })

@login_auth
@admin_required
@superadmin_required
def rekap_kehadiran(request):
    from urllib.parse import urlencode
    from datetime import datetime, time

    user_login = get_object_or_404(Users, nik=request.session['nik_id'])

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    divisi_id = request.GET.get('divisi')
    page_number = request.GET.get('page', 1)

    users_qs = Users.objects.all().order_by('divisi')

    if divisi_id:
        users_qs = users_qs.filter(divisi=divisi_id)

    rekap = []

    today = timezone.localdate()
    default_start_date = today.replace(day=1)
    default_end_date = today

    if start_date and end_date:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    else:
        start_date_obj = default_start_date
        end_date_obj = default_end_date

    start_datetime = timezone.make_aware(
        datetime.combine(start_date_obj, time.min)
    )
    end_datetime = timezone.make_aware(
        datetime.combine(end_date_obj, time.max)
    )

    for user in users_qs:
        rekap.append({
            'nik': user.nik,
            'nama': user.name,
            'divisi': user.divisi,
            'hadir': InAbsences.objects.filter(
                nik=user,
                date_in__range=(start_datetime, end_datetime),
            ).exclude(
                status_in__in=['Libur', 'Cuti', 'Izin']
            ).count(),
            'tepat_waktu': InAbsences.objects.filter(
                nik=user,
                date_in__range=(start_datetime, end_datetime),
                status_in='Tepat Waktu'
            ).count(),
            'terlambat': InAbsences.objects.filter(
                nik=user,
                date_in__range=(start_datetime, end_datetime),
                status_in='Terlambat'
            ).count(),
            'pulang_cepat': InAbsences.objects.filter(
                nik=user,
                date_out__range=(start_datetime, end_datetime),
                status_out='Pulang Cepat'
            ).count(),
            'izin': PermissionRequests.objects.filter(
                nik=user,
                start_date__lte=end_date_obj,
                end_date__gte=start_date_obj,
                status='Approved'
            ).count(),
            'cuti': LeaveRequests.objects.filter(
                nik=user,
                start_date__lte=end_date_obj,
                end_date__gte=start_date_obj,
                status='Approved'
            ).count(),
            'keluar': OutPermission.objects.filter(
                nik=user,
                date__range=(start_date_obj, end_date_obj)
            ).count(),
        })

    paginator = Paginator(rekap, 10)
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'user': user_login,
        'page_obj': page_obj,
        'query_string': urlencode(query_params),
        'start_date': start_date_obj.strftime('%Y-%m-%d'),
        'end_date': end_date_obj.strftime('%Y-%m-%d'),
        'divisi': divisi_id,
        'divisi_list': MasterDivisions.objects.all(),
        'title': 'Rekap Kehadiran Karyawan'
    }

    return render(request, 'admin/rekap/index.html', context)

@login_auth
@admin_required
@superadmin_required
def rekap_kehadiran_detail(request, nik):
    from django.db.models import Count, Sum
    from datetime import datetime, time, timedelta
    from collections import defaultdict

    user = get_object_or_404(Users, nik=request.session['nik_id'])
    
    user_detail = get_object_or_404(Users, nik=nik)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    today = timezone.localdate()

    if not start_date or not end_date:
        start_date_obj = today.replace(day=1)
        end_date_obj = today
        start_date = start_date_obj.strftime('%Y-%m-%d')
        end_date = end_date_obj.strftime('%Y-%m-%d')
    else:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()

    start_dt = timezone.make_aware(datetime.combine(start_date_obj, time.min))
    end_dt = timezone.make_aware(datetime.combine(end_date_obj, time.max))

    # ======================
    # ABSENSI
    # ======================
    hadir_tepat = InAbsences.objects.filter(
        nik=user_detail,
        date_in__range=(start_dt, end_dt),
        status_in='Tepat Waktu'
    ).count()

    hadir_terlambat = InAbsences.objects.filter(
        nik=user_detail,
        date_in__range=(start_dt, end_dt),
        status_in='Terlambat'
    ).count()

    pulang_cepat = InAbsences.objects.filter(
        nik=user_detail,
        date_out__range=(start_dt, end_dt),
        status_out='Pulang Cepat'
    ).count()

    # ======================
    # JAM KERJA & LEMBUR
    # ======================
    absen_qs = InAbsences.objects.filter(
        nik=user_detail,
        date_in__range=(start_dt, end_dt),
        date_out__isnull=False
    ).exclude(
        status_in__in=['Libur', 'Cuti', 'Izin']
    )

    total_jam_kerja = 0
    total_jam_lembur = 0

    for absen in absen_qs:
        durasi = absen.date_out - absen.date_in
        jam = durasi.total_seconds() / 3600

        total_jam_kerja += jam

    lembur_qs = Overtimes.objects.filter(
        nik=user_detail,
        overtime_date__range=(start_date_obj, end_date_obj),
        status='APPROVED'
    )

    for lembur in lembur_qs:
        durasi = lembur.end_date - lembur.start_date
        jam = durasi.total_seconds() / 3600

        total_jam_lembur += jam

    total_jam_kerja = round(total_jam_kerja, 2)
    total_jam_kerja_hms = timedelta_to_hms(timedelta(hours=total_jam_kerja))
    total_jam_lembur = round(total_jam_lembur, 2)
    total_jam_lembur_hms = timedelta_to_hms(timedelta(hours=total_jam_lembur))

    # ======================
    # CUTI PER JENIS
    # ======================
    cuti_detail = defaultdict(int)

    cuti_qs = LeaveRequests.objects.filter(
        nik=user_detail,
        status='Approved',
        start_date__lte=end_date_obj,
        end_date__gte=start_date_obj
    ).select_related('leave_type')

    for cuti in cuti_qs:
        overlap_start = max(start_date_obj, cuti.start_date)
        overlap_end = min(end_date_obj, cuti.end_date)

        days = (overlap_end - overlap_start).days + 1
        if days > 0:
            cuti_detail[cuti.leave_type.name] += days

    cuti_detail = [
        {'name': name, 'total': total}
        for name, total in cuti_detail.items()
    ]

    # ======================
    # IZIN PER JENIS
    # ======================
    izin_detail = defaultdict(int)

    izin_qs = PermissionRequests.objects.filter(
        nik=user_detail,
        status='Approved',
        start_date__lte=end_date_obj,
        end_date__gte=start_date_obj
    ).select_related('permission_type')

    for izin in izin_qs:
        overlap_start = max(start_date_obj, izin.start_date)
        overlap_end = min(end_date_obj, izin.end_date)

        days = (overlap_end - overlap_start).days + 1
        if days > 0:
            izin_detail[izin.permission_type.name] += days

    izin_detail = [
        {'name': name, 'total': total}
        for name, total in izin_detail.items()
    ]

    # ======================
    # IZIN KELUAR (OUT PERMISSION)
    # ======================
    izin_keluar_list = OutPermission.objects.filter(
        nik=user_detail,
        date__range=(start_date_obj, end_date_obj),
        status='Kembali'
    ).order_by('-date')

    total_izin_keluar = izin_keluar_list.count()

    total_durasi_keluar = izin_keluar_list.aggregate(
        total=Sum('duration_minutes')
    )['total'] or 0

    total_jam_izin_keluar = total_durasi_keluar / 60
    total_jam_izin_keluar_hms = timedelta_to_hms(timedelta(hours=total_jam_izin_keluar))

    total_jam_efektif = (
        total_jam_kerja +
        total_jam_lembur -
        total_jam_izin_keluar
    )

    if total_jam_efektif < 0:
        total_jam_efektif = 0

    total_jam_izin_keluar = round(total_jam_izin_keluar, 2)
    total_jam_efektif = round(total_jam_efektif, 2)

    total_jam_efektif_menit = total_jam_efektif * 60
    total_jam_efektif_menit = timedelta_to_hms(timedelta(minutes=total_jam_efektif_menit))

    context = {
        'user': user,
        'user_detail': user_detail,

        'hadir_tepat': hadir_tepat,
        'hadir_terlambat': hadir_terlambat,
        'pulang_cepat': pulang_cepat,
        'total_jam_kerja': total_jam_kerja,
        'total_jam_lembur': total_jam_lembur,
        'total_jam_kerja_hms': total_jam_kerja_hms,
        'total_jam_lembur_hms': total_jam_lembur_hms,

        'cuti_detail': cuti_detail,
        'izin_detail': izin_detail,

        'izin_keluar_list': izin_keluar_list,
        'total_izin_keluar': total_izin_keluar,
        'total_durasi_keluar': total_durasi_keluar,

        'total_jam_izin_keluar': total_jam_izin_keluar,
        'total_jam_izin_keluar_hms': total_jam_izin_keluar_hms,
        'total_jam_efektif': total_jam_efektif,
        'total_jam_efektif_menit': total_jam_efektif_menit,

        'start_date': start_date,
        'end_date': end_date,
        'title': 'Detail Rekap Kehadiran'
    }

    return render(request, 'admin/rekap/detail.html', context)

@login_auth
@admin_required
@superadmin_required
def rekap_kehadiran_print(request):
    from datetime import datetime, time, timedelta
    from django.db.models import Sum

    user_login = get_object_or_404(Users, nik=request.session['nik_id'])

    # ===============================
    # FILTER
    # ===============================
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    divisi = request.GET.get('divisi')

    today = timezone.localdate()

    if not start_date or not end_date:
        start_date_obj = today.replace(day=1)
        end_date_obj = today
    else:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    start_datetime = timezone.make_aware(
        datetime.combine(start_date_obj, time.min)
    )
    end_datetime = timezone.make_aware(
        datetime.combine(end_date_obj, time.max)
    )

    # ===============================
    # MASTER DATA
    # ===============================
    master_cuti = MasterLeaves.objects.all().order_by('id')
    master_izin = MasterPermission.objects.all().order_by('id')

    # ===============================
    # QUERY USER
    # ===============================
    users = Users.objects.all().order_by('divisi', 'name')

    if divisi:
        users = users.filter(divisi=divisi)

    data = []

    # ===============================
    # LOOP USER
    # ===============================
    for u in users:

        # ===============================
        # ABSENSI DASAR
        # ===============================
        hadir = InAbsences.objects.filter(
            nik=u,
            date_in__range=(start_datetime, end_datetime),
        ).exclude(
            status_in__in=['Libur', 'Cuti', 'Izin']
        ).count()

        tepat_waktu = InAbsences.objects.filter(
            nik=u,
            date_in__range=(start_datetime, end_datetime),
            status_in='Tepat Waktu'
        ).count()

        terlambat = InAbsences.objects.filter(
            nik=u,
            date_in__range=(start_datetime, end_datetime),
            status_in='Terlambat'
        ).count()

        pulang_cepat = InAbsences.objects.filter(
            nik=u,
            date_out__range=(start_datetime, end_datetime),
            status_out='Pulang Cepat'
        ).count()

        # ===============================
        # CUTI PER JENIS (HITUNG HARI)
        # ===============================
        cuti_detail = {}

        for mc in master_cuti:
            total_hari = 0

            qs = LeaveRequests.objects.filter(
                nik=u,
                leave_type=mc,
                status='Approved',
                start_date__lte=end_date_obj,
                end_date__gte=start_date_obj
            )

            for c in qs:
                s = max(c.start_date, start_date_obj)
                e = min(c.end_date, end_date_obj)
                total_hari += (e - s).days + 1

            cuti_detail[mc.name] = total_hari

        # ===============================
        # IZIN PER JENIS (HITUNG HARI)
        # ===============================
        izin_detail = {}

        for mi in master_izin:
            total_hari = 0

            qs = PermissionRequests.objects.filter(
                nik=u,
                permission_type=mi,
                status='Approved',
                start_date__lte=end_date_obj,
                end_date__gte=start_date_obj
            )

            for i in qs:
                s = max(i.start_date, start_date_obj)
                e = min(i.end_date, end_date_obj)
                total_hari += (e - s).days + 1

            izin_detail[mi.name] = total_hari

        # ===============================
        # IZIN KELUAR (JAM)
        # ===============================
        izin_keluar_qs = OutPermission.objects.filter(
            nik=u,
            date__range=(start_date_obj, end_date_obj),
            status='Kembali'
        )

        izin_keluar_count = izin_keluar_qs.count()

        total_izin_keluar_minutes = izin_keluar_qs.aggregate(
            total=Sum('duration_minutes')
        )['total'] or 0

        total_izin_keluar_td = timedelta(minutes=total_izin_keluar_minutes)

        # ===============================
        # JAM KERJA & LEMBUR
        # ===============================
        kerja = timedelta()
        lembur = timedelta()

        absensi = InAbsences.objects.filter(
            nik=u,
            date_in__range=(start_datetime, end_datetime),
            date_out__isnull=False
        ).exclude(
            status_in__in=['Libur', 'Cuti', 'Izin']
        )

        for a in absensi:
            durasi = a.date_out - a.date_in
            kerja += durasi

        lembur_qs = Overtimes.objects.filter(
            nik=u,
            overtime_date__range=(start_date_obj, end_date_obj),
            status='APPROVED'
        )

        for l in lembur_qs:
            durasi = l.end_date - l.start_date
            lembur += durasi

        # ===============================
        # TOTAL JAM FINAL
        # ===============================
        total_final_td = kerja + lembur - total_izin_keluar_td

        # ===============================
        # FORMAT TIME
        # ===============================
        jam_kerja = timedelta_to_hms(kerja)
        jam_lembur = timedelta_to_hms(lembur)
        izin_keluar_time = timedelta_to_hms(total_izin_keluar_td)
        total_jam_final = timedelta_to_hms(total_final_td)

        # ===============================
        # APPEND DATA
        # ===============================
        data.append({
            'nik': u.nik,
            'nama': u.name,
            'divisi': u.divisi or '-',

            'hadir': hadir,
            'tepat_waktu': tepat_waktu,
            'terlambat': terlambat,
            'pulang_cepat': pulang_cepat,

            'cuti_detail': cuti_detail,
            'izin_detail': izin_detail,

            'izin_keluar_count': izin_keluar_count,
            'izin_keluar_time': izin_keluar_time,

            'jam_kerja': jam_kerja,
            'jam_lembur': jam_lembur,
            'total_jam': total_jam_final,
        })

    # ===============================
    # RENDER
    # ===============================
    return render(request, 'admin/rekap/print.html', {
        'title': 'Cetak Rekap Kehadiran Karyawan',
        'user': user_login,
        'start_date': start_date_obj,
        'end_date': end_date_obj,
        'data': data,
        'master_cuti': master_cuti,
        'master_izin': master_izin,
    })

@login_auth
@admin_required
def lembur(request):
    from datetime import timedelta
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if user.is_admin == 1:
        status_filter = ['SUBMITTED']
        status_exclude = ['DRAFT', 'SUBMITTED']
        base_filter = {'approved_by': user}

    elif user.is_admin == 2:
        status_filter = ['DIVISI APPROVED']
        status_exclude = ['DRAFT', 'SUBMITTED', 'DIVISI APPROVED']
        base_filter = {}

    lembur_list = Overtimes.objects.filter(
        status__in=status_filter,
        **base_filter
    ).order_by('-overtime_date')

    done_lembur_list = Overtimes.objects.exclude(
        status__in=status_exclude
    ).filter(
        **base_filter
    )
    # lembur_list = Overtimes.objects.filter(status='SUBMITTED').order_by('-overtime_date')
    # done_lembur_list = Overtimes.objects.filter(status__in=['APPROVED', 'REJECTED']).order_by('-overtime_date')

    for lembur in lembur_list:
        second = lembur.duration_minutes * 60
        total_jam = timedelta_to_hms(timedelta(seconds=second))
        lembur.total_jam = total_jam

    for lembur in done_lembur_list:
        second = lembur.duration_minutes * 60
        total_jam = timedelta_to_hms(timedelta(seconds=second))
        lembur.total_jam = total_jam

    context = {
        'user': user,
        'lembur_list': lembur_list,
        'done_lembur_list': done_lembur_list,
        'title': 'Daftar Pengajuan Lembur Karyawan'
    }

    return render(request, 'admin/lembur/index.html', context)

@login_auth
@admin_required
def detail_lembur(request, id):
    from datetime import timedelta
    user = get_object_or_404(Users, nik=request.session['nik_id'])
    lembur = get_object_or_404(Overtimes, id=id)

    second = lembur.duration_minutes * 60
    total_jam = timedelta_to_hms(timedelta(seconds=second))
    lembur.total_jam = total_jam

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes')

        try:
            if user.is_admin == 1 and status == 'APPROVED':
                status = 'DIVISI APPROVED'

            lembur.status = status
            lembur.notes = notes
            lembur.approved_at = timezone.now()
            lembur.save()

            import pytz
            tz_jakarta = pytz.timezone('Asia/Jakarta')

            tgl_masuk_jkt = lembur.start_date.astimezone(tz_jakarta)
            tgl_pulang_jkt = lembur.end_date.astimezone(tz_jakarta)
            
            tgl_masuk_bersih = tgl_masuk_jkt.replace(tzinfo=None)
            tgl_pulang_bersih = tgl_pulang_jkt.replace(tzinfo=None)

            pesan_tgl_masuk = tgl_masuk_bersih.strftime('%d %b %Y, %H:%M')
            pesan_tgl_pulang = tgl_pulang_bersih.strftime('%d %b %Y, %H:%M')

            if user.is_admin == 1 and  status == 'DIVISI APPROVED':
                message = f"""
📢 <b>Pengajuan Lembur Baru</b>

Nama: {lembur.nik.name}
Total: {lembur.duration_minutes}  menit
Tanggal: {pesan_tgl_masuk} s.d. {pesan_tgl_pulang}
Alasan: {lembur.reason}
PJ Unit: {lembur.approved_by.name}

https://s.id/asidewa

Silakan klik tautan di atas dan pilih menu <b>Persetujuan Lembur</b> untuk melakukan approval.
            """
                hrd_list = Users.objects.filter(is_admin=2).exclude(telegram_chat_id=None)

                send_telegram_message_hrd(hrd_list, message)

            if user.is_admin == 2 and status != 'DIVISI APPROVED' and lembur.nik.telegram_chat_id:
                message = f"""
📢 <b>Persetujuan Lembur</b>

Nama: {lembur.nik.name}
Total: {lembur.duration_minutes}  menit
Tanggal: {pesan_tgl_masuk} s.d. {pesan_tgl_pulang}
Catatan: {notes}
Status: <b>{status}</b>

Silakan check data lembur Anda, dengan hasil pengajuan ini.

<i>Hubungi Unit IT jika terdapat kesalahan.</i>
            """
                send_telegram_message(lembur.nik.telegram_chat_id, message)

            messages.success(request, 'Data persetujuan lembur berhasil disimpan.')
            return redirect('/admins/lembur')

        except Exception as e:
            messages.error(
                request,
                f'Gagal menyimpan data persetujuan lembur. Error: {e}'
            )
            return redirect('/admins/lembur')
        
    status_choices = (
        ['Pending', 'Approved', 'Rejected']
        if user.is_admin == 1
        else ['Approved', 'Rejected']
    )   

    context = {
        'user': user,
        'lembur': lembur,
        'title': 'Detail Pengajuan Lembur Karyawan',
        'status_choices': status_choices
    }   
    return render(request, 'admin/lembur/detail.html', context)