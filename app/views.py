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
        cached_enc = cache.get("known_face_encodings")
        cached_users = cache.get("known_face_users")

        if cached_enc is None:
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

            cache.set("known_face_encodings", known_encodings, 3600)
            cache.set("known_face_users", user_list, 3600)
        else:
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

        if best_distance > 0.55:
            return JsonResponse({
                'status': 'error',
                'message': 'Gagal mengenali wajah'
            })

        user = user_list[best_idx]
        print(f'Name: {user.name}')

        # ======================================================
        # 7. LOGIC ABSENSI 
        # ======================================================
        from django.utils import timezone

        now = timezone.localtime(timezone.now())
        today = now.date()
        tz_jakarta = pytz.timezone('Asia/Jakarta')

        # ---------- ABSEN PULANG ----------
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

            return JsonResponse({
                'status': 'success',
                'type': 'Pulang',
                'message': 'Absen pulang berhasil',
                'status_absen': status_out,
                'nik': user.nik,
                'name': user.name,
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'minor_message': 'Hati-hati di Jalan 🛵'
            })

        # ---------- CEK SUDAH ABSEN HARI INI ----------
        if InAbsences.objects.filter(
            nik=user,
            date_in__date=today,
            date_out__isnull=False
        ).exists():

            schedule_name = (
                MappingSchedules.objects.filter(nik=user, date=today)
                .values_list("schedule__name", flat=True)
                .first()
            )

            msg_map = {
                "Libur": "Tidak ada jadwal untuk hari ini. Libur... Boss",
                "Cuti": "Tidak ada jadwal untuk hari ini. Katanya mau cuti !!"
            }

            return JsonResponse({
                'status': 'error',
                'message': msg_map.get(
                    schedule_name,
                    "Anda sudah absen pulang hari ini..."
                )
            })

        # ---------- ABSEN MASUK ----------
        schedule_today = MappingSchedules.objects.filter(
            nik=user, date=today
        ).select_related("schedule").first()

        if not schedule_today or schedule_today.schedule.name == "Libur":
            return JsonResponse({
                'status': 'error',
                'message': 'Tidak ada jadwal untuk hari ini. Libur... Boss'
            })

        sched = schedule_today.schedule
        jadwal_in_today = timezone.make_aware(datetime.combine(today, sched.start_time), tz_jakarta)
        status_in = "Tepat Waktu" if now <= jadwal_in_today else "Terlambat"

        InAbsences.objects.create(
            nik=user,
            date_in=now,
            status_in=status_in,
            schedule=sched
        )

        return JsonResponse({
            'status': 'success',
            'type': 'Masuk',
            'message': 'Absen masuk berhasil',
            'status_absen': status_in,
            'nik': user.nik,
            'name': user.name,
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'minor_message': 'Semangat Bekerja 💪🏼'
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
        )

        # if photo_file:
        #     new_leave_request.photo = photo_file

        new_leave_request.save()

        messages.success(request, 'Pengajuan cuti berhasil diupload.')
        return redirect('/users/pengajuan_cuti')

    cuti_list = MasterLeaves.objects.all()
    pengajuan_list = LeaveRequests.objects.filter(nik_id=user.nik)

    context = {
        'user': user,
        'cuti_list': cuti_list,
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

        try:
            pengajuan = get_object_or_404(LeaveRequests, id=id)

            pengajuan.leave_type =  leave_type_obj
            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.reason = reason

            # if(photo_file):
            #    pengajuan.photo = photo_file

            pengajuan.save() 

            messages.success(request, 'Data perubahan pengajuan cuti berhasil diupload.')
            return redirect('/users/pengajuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal mengupload perubahan data pengajuan cuti. Error: {e}')
            return redirect('/users/pengajuan_cuti')

    context = {
       'user': user,
       'cuti_list':cuti_list,
       'pengajuan': pengajuan,
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

    jadwal_bulanan = []

    data = MappingSchedules.objects.filter(
        nik=user,
        date__month=bulan,
        date__year=tahun
    ).select_related("schedule")

    mapping = {
        item.date.day: item.schedule.name 
            if item.schedule.name in ["Libur", "Cuti"]
            else item.schedule.start_time.strftime("%H:%M")
        for item in data
    }

    for d in range(1, total_hari + 1):
        current_date = date(tahun, bulan, d)
        hari_text = calendar.day_name[current_date.weekday()]

        jadwal_bulanan.append({
            "tanggal": d,
            "hari": hari_text,
            "jadwal": mapping.get(d, "-")
        })

    context = {
        "user": user,
        "jadwal_bulanan": jadwal_bulanan,
        "bulan_text": bulan_text,
        "tahun": tahun,
        'title': 'Jadwal Saya'
    }

    return render(request, "user/jadwal/index.html", context)

@login_auth
def presensi(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    today = date.today()
    bulan = today.month
    tahun = today.year

    absensis = InAbsences.objects.filter(
        nik=user,
        date_in__month=bulan,
        date_in__year=tahun
    ).order_by('-date_in')

    absensi_bulanan = []
    for abs in absensis:
        absensi_bulanan.append({
            "tanggal": abs.date_in.day,
            "hari": abs.date_in.strftime("%A"),
            "jam_in": abs.schedule.start_time.strftime("%H:%M") if abs.schedule.start_time else None,
            "status_in": abs.status_in,
            "jam_out": abs.schedule.end_time.strftime("%H:%M") if abs.schedule.end_time else None,
            "status_out": abs.status_out,
        })

    context = {
        'user': user,
        "bulan_text": calendar.month_name[bulan],
        "tahun": tahun,
        "absensi_bulanan": absensi_bulanan,
        "title": 'Riwayat absen saya '
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
            return redirect('/users/profile', nik=detail_user.nik)
        
        except Exception as e:
            messages.error(request, f'Gagal mengupdate data Anda: {e}')
            
            return redirect('/users/profile', nik=detail_user.nik) 

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


