from urllib import request
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile  
from datetime import datetime, timedelta
from cms.decorators import login_auth
from django.utils.timezone import now
from django.http import JsonResponse
from django.contrib import messages
from datetime import date, datetime
from django.core.cache import cache
from cms.models import *
import face_recognition
from .models import *
from PIL import Image
import numpy as np
import calendar
import base64
import pickle
import pytz
import cv2
import io

# Create your views here.

def calculate_dynamic_threshold(encodings, safety_factor=0.85):
    if len(encodings) < 2:
        return 0.45 

    distances = []

    for i in range(len(encodings)):
        for j in range(i + 1, len(encodings)):
            d = np.linalg.norm(encodings[i] - encodings[j])
            distances.append(d)

    min_dist = np.min(distances)
    # print(f'{min_dist}')

    dynamic_threshold = min_dist * safety_factor

    dynamic_threshold = max(0.35, min(dynamic_threshold, 0.6))

    return round(dynamic_threshold, 3)

def detect_glare(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = np.array(img)

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    bright_pixels = np.sum(gray > 230) / gray.size

    print(f'bright = {bright_pixels}')

    if bright_pixels > 0.12:
        return True, "Terdeteksi pantulan glare yang tidak natural."

    b, g, r = cv2.split(img)
    blue_ratio = np.mean(b) / (np.mean(r) + 1)

    if blue_ratio > 1.25:
        return True, "Warna dominan biru, terindikasi foto layar. Pakai foto dari HP ya ??"

    return False, None

def absence(request):
    if request.method != 'POST':
        return render(request, 'user/absence.html')

    try:
        # ======================================================
        # 1. AMBIL & VALIDASI BASE64 FOTO
        # ======================================================
        photo_data = request.POST.get('photo')
        if not photo_data:
            return JsonResponse({'status': 'error', 'message': 'Foto tidak valid'})

        try:
            format, imgstr = photo_data.split(';base64,')
            ext = format.split('/')[-1]
            img_bytes = base64.b64decode(imgstr)
        except Exception:
            return JsonResponse({'status': 'error', 'message': 'Format foto tidak valid'})

        # ======================================================
        # 2. SIMPAN FILE TEMPORARY 
        # ======================================================
        import uuid
        temp_name = f"temp_face_{uuid.uuid4().hex}.{ext}"
        temp_path = default_storage.save(temp_name, ContentFile(img_bytes))
        temp_full = default_storage.path(temp_path)

        # ======================================================
        # 3. LOAD + PREPROCESS IMAGE
        # ======================================================
        img = cv2.imread(temp_full)
        if img is None:
            return JsonResponse({
                'status': 'error',
                'message': 'Gagal membaca gambar wajah'
            })

        h, w, _ = img.shape
        if h < 80 or w < 80:
            return JsonResponse({
                'status': 'error',
                'message': 'Wajah terlalu kecil / terlalu jauh'
            })

        # Resize konsisten (WAJIB)
        # img = cv2.resize(img, (160, 160))

        # BGR → RGB
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # ======================================================
        # 4. FACE ENCODING
        # ======================================================
        uploaded_encs = face_recognition.face_encodings(rgb)
        if not uploaded_encs:
            return JsonResponse({
                'status': 'error',
                'message': 'Wajah tidak terdeteksi'
            })

        uploaded_enc = uploaded_encs[0]

        # ======================================================
        # 5. LOAD CACHE ENCODING USER
        # ======================================================
        db_count = Users.objects.exclude(face_encoding=None).count()

        cached_enc = cache.get("known_face_encodings")
        cached_users = cache.get("known_face_users")

        if not cached_enc or len(cached_enc) != db_count:
            users = Users.objects.exclude(face_encoding=None).only(
                "nik", "name", "face_encoding"
            )

            known_encodings = []
            user_list = []

            for u in users:
                try:
                    known_encodings.append(pickle.loads(u.face_encoding))
                    user_list.append(u)
                except Exception:
                    continue

            cache.set("known_face_encodings", known_encodings, 86400)
            cache.set("known_face_users", user_list, 86400)

            print("DB count:", db_count)
            print(f"Cache Re-loaded. Total: {len(known_encodings)}")
        else:
            print("Menggunakan data dari cache.")
            known_encodings = cached_enc
            user_list = cached_users

        if not known_encodings:
            return JsonResponse({
                'status': 'error',
                'message': 'Tidak ada data wajah terdaftar'
            })

        # ======================================================
        # 6. MATCHING
        # ======================================================
        threshold = calculate_dynamic_threshold(known_encodings)
        print(f'Thershold: {threshold}')
        distances = face_recognition.face_distance(known_encodings, uploaded_enc)

        best_idx = np.argmin(distances)
        best_distance = distances[best_idx]
        print(f'User encode: {best_distance}')

        if best_distance > 0.4:
            return JsonResponse({
                'status': 'error',
                'message': 'Gagal mengenali wajah, coba lagi ya...'
            })

        user = user_list[best_idx]
        print(f'Name: {user.name}')

        # ======================================================
        # 7. LOGIC ABSENSI 
        # ======================================================
        from django.utils import timezone
        from datetime import time

        now = timezone.localtime(timezone.now())
        today = now.date()
        tz_jakarta = pytz.timezone('Asia/Jakarta')
        start_of_day = timezone.make_aware(datetime.combine(today, time.min), tz_jakarta)
        end_of_day = timezone.make_aware(datetime.combine(today, time.max), tz_jakarta)

        # ================================
        # ABSEN PULANG (SHIFT AKTIF)
        # ================================
        existing_absen = (
            InAbsences.objects.filter(nik=user, date_out__isnull=True)
            .only("date_in", "schedule")
            .order_by('-date_in')
            .first()
        )

        if existing_absen:
            sched = existing_absen.schedule
            date_in_day = existing_absen.date_in.date()

            jadwal_in = timezone.make_aware(datetime.combine(date_in_day, sched.start_time), tz_jakarta)
            jadwal_out = timezone.make_aware(datetime.combine(date_in_day, sched.end_time), tz_jakarta)

            if jadwal_out < jadwal_in:
                jadwal_out += timedelta(days=1)

            status_out = "Pulang Cepat" if now < jadwal_out else "Tepat Waktu"

            existing_absen.date_out = now
            existing_absen.status_out = status_out
            existing_absen.save()

            time = MasterSchedules.objects.get(id=existing_absen.schedule.id)

            print(f'Absen pulang shift {existing_absen.shift_order} - {time.start_time}')

            return JsonResponse({
                'status': 'success',
                'type': 'Pulang',
                'shift': existing_absen.shift_order,
                'message': f'Absen pulang shift {time.start_time} berhasil',
                'status_absen': status_out,
                'nik': user.nik,
                'name': user.name,
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'minor_message': 'Hati-hati di Jalan 🛵'
            })

        # ================================
        # CEK JADWAL & STATUS (SHIFT)
        # ================================-
        jadwal_list = MappingSchedules.objects.filter(
            nik=user,
            date=today
        ).select_related("schedule").order_by("shift_order")

        if not jadwal_list.exists():
            print(f'Absen Belum di mapping')
            return JsonResponse({'status': 'error', 'message': f'Hari ini tidak ada jadwal untuk {user.name}. Hubungi PJ/PIC jika ini sebuah kesalahan.'})

        first_schedule_name = jadwal_list[0].schedule.name
        msg_map = {
            "Libur": f'{user.name}, hari ini anda libur. Tidak perlu absen ya!',
            "Cuti": f'{user.name}, hari ini anda cuti. Tidak perlu absen ya!'
        }

        if first_schedule_name in msg_map:
            print(f'Absen Libur/Cuti: {first_schedule_name}')
            return JsonResponse({
                'status': 'error',
                'message': msg_map[first_schedule_name]
            })

        # ================================
        # ABSEN MASUK (SHIFT BERIKUTNYA)
        # ================================
        for jadwal in jadwal_list:
            sudah_masuk = InAbsences.objects.filter(
                nik=user,
                shift_order=jadwal.shift_order,
                date_in__range=(start_of_day, end_of_day),
                date_out__isnull=False
            ).exists()

            if not sudah_masuk:
                sched = jadwal.schedule

                jadwal_in_today = timezone.make_aware(
                    datetime.combine(today, sched.start_time),
                    tz_jakarta
                )

                status_in = "Tepat Waktu" if now <= jadwal_in_today else "Terlambat"

                InAbsences.objects.create(
                    nik=user,
                    date_in=now,
                    status_in=status_in,
                    schedule=sched,
                    shift_order=jadwal.shift_order
                )
                print(f'Absen masuk shift {jadwal.shift_order} - {sched.start_time}')
                return JsonResponse({
                    'status': 'success',
                    'type': 'Masuk',
                    'shift': jadwal.shift_order,
                    'message': f'Absen masuk shift {jadwal.schedule.start_time} berhasil',
                    'status_absen': status_in,
                    'nik': user.nik,
                    'name': user.name,
                    'date': now.strftime('%Y-%m-%d'),
                    'time': now.strftime('%H:%M:%S'),
                    'minor_message': 'Semangat Bekerja 💪🏼'
                })

        # ================================
        # SEMUA SHIFT SELESAI
        # ================================
        print(f'Semua shift sudah absen')
        return JsonResponse({
            'status': 'error',
            'message': f'{user.name}, Anda sudah absen pulang untuk semua shift hari ini.'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })

    finally:
        if 'temp_path' in locals():
            default_storage.delete(temp_path)

@login_auth
def pengajuan_cuti(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
        leave_type_id = request.POST['cuti']
        leave_type_obj = get_object_or_404(MasterLeaves, id=leave_type_id)
        # photo_file = request.FILES.get('photo')
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        reason = request.POST['reason']
        boss = request.POST['boss']

        boss_obj = get_object_or_404(Users, nik=boss)

        current_year = now().year

        kuota_tidak_dibatasi = (leave_type_obj.default_quota == 0)

        pengajuan_tahun_ini = LeaveRequests.objects.filter(
            nik_id=user.nik,
            leave_type_id=leave_type_id,
            created_at__year=current_year
        )

        total_hari_terpakai = 0
        for pengajuan in pengajuan_tahun_ini:
            total_hari_terpakai += (pengajuan.end_date - pengajuan.start_date).days + 1

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        hari_cuti_baru = (end_date_obj - start_date_obj).days + 1

        if not kuota_tidak_dibatasi:
            if total_hari_terpakai + hari_cuti_baru > leave_type_obj.default_quota:
                messages.error(
                    request,
                    (
                        f"Pengajuan gagal! Total hari cuti '{leave_type_obj.name}' "
                        f"yang diajukan ({hari_cuti_baru} hari) + yang sudah digunakan "
                        f"({total_hari_terpakai} hari) melebihi kuota "
                        f"{leave_type_obj.default_quota} hari."
                    )
                )
                return redirect('/users/pengajuan_cuti')

        new_leave_request = LeaveRequests(
            nik=user,
            leave_type=leave_type_obj,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            user_target=boss_obj
        )

        # if photo_file:
        #     new_leave_request.photo = photo_file

        new_leave_request.save()

        messages.success(request, 'Pengajuan cuti berhasil diupload.')
        return redirect('/users/pengajuan_cuti')

    cuti_list = MasterLeaves.objects.all()
    boss_list = Users.objects.filter(is_admin__in=[1,2])
    pengajuan_list = LeaveRequests.objects.filter(nik_id=user.nik)

    context = {
        'user': user,
        'cuti_list': cuti_list,
        'boss_list': boss_list,
        'pengajuan_list': pengajuan_list,
        'title': 'Pengajuan Cuti'
    }

    return render(request, 'user/cuti/index.html', context)

@login_auth
def edit_pengajuan_cuti(request, id):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    cuti_list = MasterLeaves.objects.all()

    pengajuan = get_object_or_404(
        LeaveRequests, 
        nik_id=user.nik, 
        id=id
    )

    if request.method == 'POST':
        leave_type_id = request.POST['cuti']
        leave_type_obj = get_object_or_404(MasterLeaves, id=leave_type_id)
        # photo_file = request.FILES.get('photo') 
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        reason = request.POST['reason']
        boss = request.POST['boss']

        boss_obj = get_object_or_404(Users, nik=boss)

        try:
            pengajuan = get_object_or_404(LeaveRequests, id=id)

            pengajuan.leave_type =  leave_type_obj
            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.reason = reason
            pengajuan.user_target = boss_obj


            # if(photo_file):
            #    pengajuan.photo = photo_file

            pengajuan.save() 

            messages.success(request, 'Data perubahan pengajuan cuti berhasil diupload.')
            return redirect('/users/pengajuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal mengupload perubahan data pengajuan cuti. Error: {e}')
            return redirect('/users/pengajuan_cuti')

    boss_list = Users.objects.filter(is_admin__in=[1,2])

    context = {
       'user': user,
       'cuti_list':cuti_list,
       'pengajuan': pengajuan,
       'boss_list': boss_list,
       'title': 'Edit Pengajuan Cuti'
    }

    return render(request, 'user/cuti/editForm.html', context)

@login_auth
def delete_pengajuan_cuti(request, id):
    try:
      cuti = get_object_or_404(LeaveRequests, id=id)
      cuti.delete()

      messages.success(request, 'Data pengajuan cuti berhasil dihapus.')
      return redirect('/users/pengajuan_cuti')
    
    except Exception as e:
      messages.error(request, f'Gagal menghapus data pengajuan cuti: {e}')
      return redirect('/users/pengajuan_cuti')

@login_auth
def jadwal(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    today = date.today()
    bulan = today.month
    tahun = today.year

    bulan_text = calendar.month_name[bulan]
    total_hari = calendar.monthrange(tahun, bulan)[1]

    # ================================
    # AMBIL SEMUA JADWAL BULAN INI
    # ================================
    data = (
        MappingSchedules.objects.filter(
            nik=user,
            date__month=bulan,
            date__year=tahun
        )
        .select_related("schedule")
        .order_by("date", "shift_order")
    )

    # ================================
    # GROUP BY TANGGAL
    # ================================
    mapping = {}

    for item in data:
        day = item.date.day
        sched = item.schedule

        if day not in mapping:
            mapping[day] = []

        if sched.name in ["Libur", "Cuti", "Izin"]:
            mapping[day] = [sched.name] 
        else:
            mapping[day].append(
                f"{sched.start_time.strftime('%H:%M')} - {sched.end_time.strftime('%H:%M')}"
            )

    # ================================
    # BENTUK DATA PER HARI
    # ================================
    jadwal_bulanan = []

    for d in range(1, total_hari + 1):
        current_date = date(tahun, bulan, d)
        hari_text = calendar.day_name[current_date.weekday()]

        jadwal_hari = mapping.get(d, [])

        jadwal_bulanan.append({
            "tanggal": d,
            "hari": hari_text,
            "jadwal": jadwal_hari if jadwal_hari else ["-"]
        })

    context = {
        "user": user,
        "jadwal_bulanan": jadwal_bulanan,
        "bulan_text": bulan_text,
        "tahun": tahun,
        "title": "Jadwal Saya"
    }

    return render(request, "user/jadwal/index.html", context)

@login_auth
def presensi(request):
    from django.utils import timezone
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    today = timezone.localdate()
    bulan = today.month
    tahun = today.year

    start_month = timezone.make_aware(datetime(tahun, bulan, 1))
    end_month = (
        timezone.make_aware(datetime(tahun + 1, 1, 1))
        if bulan == 12
        else timezone.make_aware(datetime(tahun, bulan + 1, 1))
    )

    absensis = InAbsences.objects.filter(
        nik=user,
        date_in__gte=start_month,
        date_in__lt=end_month
    ).select_related("schedule").order_by("date_in")

    absensi_bulanan = []

    for abs in absensis:
        date_in_local = timezone.localtime(abs.date_in) if abs.date_in else None
        date_out_local = timezone.localtime(abs.date_out) if abs.date_out else None

        absensi_bulanan.append({
            "tanggal": date_in_local.day if date_in_local else "-",
            "hari": date_in_local.strftime("%A") if date_in_local else "-",
            "jam_in": date_in_local.strftime("%H:%M") if date_in_local else None,
            "status_in": abs.status_in,
            "jam_out": date_out_local.strftime("%H:%M") if date_out_local else None,
            "status_out": abs.status_out,
        })

    context = {
        "user": user,
        "bulan_text": calendar.month_name[bulan],
        "tahun": tahun,
        "absensi_bulanan": absensi_bulanan,
        "title": "Riwayat absen saya"
    }

    return render(request, "user/absensi/index.html", context)

@login_auth
def profile(request, nik):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    detail_user = get_object_or_404(Users, nik=nik)

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        divisi = request.POST.get('divisi')
        password_baru = request.POST.get('password')
        
        try:
            detail_user.name = name
            detail_user.email = email
            detail_user.divisi = divisi

            if password_baru:
                detail_user.password = make_password(password_baru)

            detail_user.save()

            messages.success(request, 'Data Anda berhasil diupdate.')
            return redirect('profile', nik=user.nik)
        
        except Exception as e:
            messages.error(request, f'Gagal mengupdate data Anda: {e}')
            
            return redirect('profile', nik=user.nik) 

    division_detail = None
    if detail_user.divisi:
        try:
            division_detail = MasterDivisions.objects.get(id=detail_user.divisi)
        except MasterDivisions.DoesNotExist:
            pass

    context = {
        'user': user,
        'detail_user': detail_user,
        'division_detail': division_detail,
        'title': 'Profile ' + detail_user.name
    }

    return render(request, 'user/profile/index.html', context)

@login_auth
def pengajuan_izin(request):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    if request.method == 'POST':
        permission_type_id = request.POST.get('izin')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        reason = request.POST.get('reason')
        boss_nik = request.POST.get('boss')
        photo_file = request.FILES.get('photo')

        permission_type = get_object_or_404(MasterPermission, id=permission_type_id)
        boss_obj = get_object_or_404(Users, nik=boss_nik)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        from django.utils.html import format_html

        if permission_type.max_days and permission_type.max_days > 0:
            end_date = start_date + timedelta(days=permission_type.max_days - 1)
        else:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if end_date < start_date:
            messages.error(request, "Tanggal selesai tidak valid.")
            return redirect('/users/pengajuan_izin')

        if permission_type.is_requires_attachment and not photo_file:
            messages.error(
                request,
                format_html(
                    "Izin {} memerlukan lampiran foto.",
                    permission_type.name
                )
            )
            return redirect('/users/pengajuan_izin')

        # from django.db.models import Q
        if permission_type.max_per_month is not None and permission_type.max_per_month > 0:
            pengajuan_bulan_ini = PermissionRequests.objects.filter(
                nik=user,
                permission_type=permission_type,
                start_date__year=start_date.year, start_date__month=start_date.month
            # # ).filter(
            #     Q(start_date__year=start_date.year, start_date__month=start_date.month) |
            #     Q(end_date__year=start_date.year, end_date__month=start_date.month) |
            #     Q(start_date__lt=start_date, end_date__gt=start_date)
            ).count()

            if pengajuan_bulan_ini >= permission_type.max_per_month:
                messages.error(
                    request,
                    format_html(
                        "Izin {} hanya dapat diajukan {} kali per bulan.",
                        permission_type.name,
                        permission_type.max_per_month
                    )
                )
                return redirect('/users/pengajuan_izin')

        PermissionRequests.objects.create(
            nik=user,
            permission_type=permission_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            user_target=boss_obj,
            photo=photo_file
        )

        messages.success(
            request,
            format_html(
                "Pengajuan izin {} berhasil dikirim.",
                permission_type.name
            )
        )
        return redirect('/users/pengajuan_izin')

    context = {
        'user': user,
        'izin_list': MasterPermission.objects.all(),
        'boss_list': Users.objects.filter(is_admin__in=[1, 2]),
        'pengajuan_list': PermissionRequests.objects.filter(nik=user).order_by('-created_at'),
        'title': 'Pengajuan Izin'
    }

    return render(request, 'user/izin/index.html', context)

@login_auth
def edit_pengajuan_izin(request, id):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    pengajuan = get_object_or_404(
        PermissionRequests,
        nik=user,
        id=id
    )

    if request.method == 'POST':
        permission_type_id = request.POST.get('izin')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        reason = request.POST.get('reason')
        boss_nik = request.POST.get('boss')
        photo_file = request.FILES.get('photo')

        permission_type = get_object_or_404(MasterPermission, id=permission_type_id)
        boss_obj = get_object_or_404(Users, nik=boss_nik)

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        from django.utils.html import format_html

        if permission_type.max_days and permission_type.max_days > 0:
            end_date = start_date + timedelta(days=permission_type.max_days - 1)
        else:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        if end_date < start_date:
            messages.error(request, "Tanggal selesai tidak valid.")
            return redirect(f'/users/pengajuan_izin/edit/{id}')

        if permission_type.is_requires_attachment and not photo_file and not pengajuan.photo:
            messages.error(
                request,
                format_html(
                    "Izin {} memerlukan lampiran foto.",
                    permission_type.name
                )
            )
            return redirect(f'/users/pengajuan_izin/edit/{id}')

        pengajuan.permission_type = permission_type
        pengajuan.start_date = start_date
        pengajuan.end_date = end_date
        pengajuan.reason = reason
        pengajuan.user_target = boss_obj

        if photo_file:
            pengajuan.photo = photo_file

        pengajuan.save()

        messages.success(
            request,
            format_html(
                "Perubahan pengajuan izin {} berhasil disimpan.",
                permission_type.name
            )
        )
        return redirect('/users/pengajuan_izin')

    context = {
        'user': user,
        'izin_list': MasterPermission.objects.all(),
        'boss_list': Users.objects.filter(is_admin__in=[1, 2]),
        'pengajuan': pengajuan,
        'title': 'Edit Pengajuan Izin'
    }

    return render(request, 'user/izin/editForm.html', context)

@login_auth
def delete_pengajuan_izin(request, id):
    try:
        pengajuan = get_object_or_404(
            PermissionRequests,
            id=id
        )
        pengajuan.delete()

        messages.success(request, 'Data pengajuan izin berhasil dihapus.')
        return redirect('/users/pengajuan_izin')

    except Exception as e:
        messages.error(request, f'Gagal menghapus data pengajuan izin: {e}')
        return redirect('/users/pengajuan_izin')
