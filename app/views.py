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

def is_long_shift(shift1, shift2, max_gap_minutes=60):
    from datetime import datetime, timedelta
    gap = (
        datetime.combine(date.today(), shift2.start_time) -
        datetime.combine(date.today(), shift1.end_time)
    )
    return timedelta(0) <= gap <= timedelta(minutes=max_gap_minutes)

def decode_base64_image(photo_data):
    try:
        format, imgstr = photo_data.split(';base64,')
        ext = format.split('/')[-1]
        img_bytes = base64.b64decode(imgstr)
        return img_bytes, ext
    except Exception:
        return None, None

def extract_face_encoding(img_bytes, ext):
    import uuid
    temp_path = None
    try:
        temp_name = f"temp_face_{uuid.uuid4().hex}.{ext}"
        temp_path = default_storage.save(temp_name, ContentFile(img_bytes))
        temp_full = default_storage.path(temp_path)

        img = cv2.imread(temp_full)
        if img is None:
            return None, "Gagal membaca gambar wajah"

        h, w, _ = img.shape
        if h < 80 or w < 80:
            return None, "Wajah terlalu kecil / terlalu jauh"

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        encodings = face_recognition.face_encodings(rgb)
        if not encodings:
            return None, "Wajah tidak terdeteksi"

        return encodings[0], None
    finally:
        if temp_path and default_storage.exists(temp_path):
            default_storage.delete(temp_path)

def get_known_faces_from_cache(UserModel):
    """Mengambil data encoding wajah dari cache atau database."""
    db_count = UserModel.objects.exclude(face_encoding=None).count()
    cached_enc = cache.get("known_face_encodings")
    cached_users = cache.get("known_face_users")

    if not cached_enc or len(cached_enc) != db_count:
        users = UserModel.objects.exclude(face_encoding=None).only(
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
        return known_encodings, user_list
    
    return cached_enc, cached_users

def choose_mode(request):
    mode = request.POST.get("mode")
    print(f'Mode chosen: {mode}')
    if mode == "ABSEN":
        return absence(request)
    elif mode == "LEMBUR":
        return overtime(request)
    else:
        return JsonResponse({"status": "error", "message": "Mode tidak valid"})

def absence(request):
    if request.method != 'POST':
        return render(request, 'user/absence.html')

    try:
        # 1. Ambil & Validasi Input
        photo_data = request.POST.get('photo')
        if not photo_data:
            return JsonResponse({'status': 'error', 'message': 'Foto tidak ditemukan'})

        # 2. Decode Base64
        img_bytes, ext = decode_base64_image(photo_data)
        if not img_bytes:
            return JsonResponse({'status': 'error', 'message': 'Format foto tidak valid'})

        # 3. Ambil Encoding dari Foto Upload
        uploaded_enc, error_msg = extract_face_encoding(img_bytes, ext)
        if error_msg:
            return JsonResponse({'status': 'error', 'message': error_msg})

        # 4. Ambil Data Wajah Terdaftar (Cache/DB)
        known_encodings, user_list = get_known_faces_from_cache(Users)
        if not known_encodings:
            return JsonResponse({'status': 'error', 'message': 'Tidak ada data wajah terdaftar'})
        
        # ======================================================
        # 5. LOAD ENCODING USER (TANPA CACHE)
        # ======================================================
        # users = Users.objects.exclude(face_encoding=None).only(
        #     "nik", "name", "face_encoding"
        # )

        # known_encodings = []
        # user_list = []

        # for u in users:
        #     try:
        #         known_encodings.append(pickle.loads(u.face_encoding))
        #         user_list.append(u)
        #     except Exception:
        #         continue

        # if not known_encodings:
        #     return JsonResponse({
        #         'status': 'error',
        #         'message': 'Tidak ada data wajah terdaftar'
        #     })

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
            # ==============================
            # CEK APAKAH PULANG LONG SHIFT
            # ==============================
            long_shift_absen = list(
                InAbsences.objects.filter(
                    nik=user,
                    status_out__isnull=True,
                    # date_in__gte=now - timedelta(hours=24)
                )
                .select_related("schedule").order_by("shift_order")
            )

            print(long_shift_absen)

            is_long_shift_active = (
                len(long_shift_absen) == 2 and
                long_shift_absen[0].date_out is not None and
                long_shift_absen[1].date_out is None
            )

            if is_long_shift_active:
                shift1, shift2 = long_shift_absen

                sched1 = shift1.schedule
                sched2 = shift2.schedule

                date_in_day1 = shift1.date_in.date()
                date_in_day2 = shift2.date_in.date()

                end_shift1 = timezone.make_aware(
                    datetime.combine(date_in_day1, sched1.end_time),
                    tz_jakarta
                )

                end_shift2 = timezone.make_aware(
                    datetime.combine(date_in_day2, sched2.end_time),
                    tz_jakarta
                )

                print(f'end_shift1: {end_shift1}, end_shift2: {end_shift2}, now: {now}')

                if end_shift1 <= timezone.localtime(shift1.date_in): 
                    end_shift1 += timedelta(days=1) 
                if end_shift2 <= timezone.localtime(shift2.date_in): 
                    end_shift2 += timedelta(days=1) 

                if now < end_shift1:
                    status_out = "Pulang Cepat"
                elif now < end_shift2:
                    status_out = "Pulang Cepat"
                else:
                    status_out = "Tepat Waktu"

                request.session["pending_absence"] = {
                    "mode": "PULANG_LONG",
                    "user_id": user.nik,
                    "time": now.isoformat()
                }

                return JsonResponse({
                    "status": "success",
                    "type": "Pulang (Long Shift)",
                    "shift": f"{shift1.shift_order}-{shift2.shift_order}",
                    "message": (
                        f"Tanggal <b>{today}</b> shift "
                        f"<b>{sched1.start_time} - {sched2.end_time}</b>"
                    ),
                    "status_absen": status_out,
                    "nik": user.nik,
                    "name": user.name,
                    "date": now.strftime('%Y-%m-%d'),
                    "time": now.strftime('%H:%M:%S'),
                    "minor_message": "Hati-hati di jalan 🛵"
                }) 
            
            sched = existing_absen.schedule
            if not sched:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Data jadwal ID: {sched.id} pada absen masuk Anda tidak ditemukan. Hubungi Admin.'
                })
        
            date_in_day = existing_absen.date_in.date()

            jadwal_in = timezone.make_aware(datetime.combine(date_in_day, sched.start_time), tz_jakarta)
            jadwal_out = timezone.make_aware(datetime.combine(date_in_day, sched.end_time), tz_jakarta)

            if jadwal_out < jadwal_in:
                jadwal_out += timedelta(days=1)
 
            status_out = "Pulang Cepat" if now < jadwal_out else "Tepat Waktu"

            # if existing_absen:
            request.session["pending_absence"] = {
                "mode": "PULANG",
                "absence_id": existing_absen.id,
                "status_out": status_out,
                "time": now.isoformat()
            }

            time = MasterSchedules.objects.get(id=existing_absen.schedule.id)

            print(f'Absen pulang tanggal {existing_absen.date_in.date()} shift {existing_absen.shift_order} - {time.start_time}')

            return JsonResponse({
                'status': 'success',
                'type': 'Pulang',
                'shift': existing_absen.shift_order,
                'message': f'Tanggal <b>{existing_absen.date_in.date()}</b> shift <b>{time.start_time} - {time.end_time}</b>',
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
            "Cuti": f'{user.name}, hari ini anda cuti. Tidak perlu absen ya!',
            "Izin": f'{user.name}, hari ini anda izin. Tidak perlu absen ya!'
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
        jadwal1 = jadwal_list[0]
        jadwal2 = jadwal_list[1] if len(jadwal_list) > 1 else None

        # =====================================================
        # LONG SHIFT (2 SHIFT BERURUTAN)
        # =====================================================
        if jadwal2 and is_long_shift(jadwal1.schedule, jadwal2.schedule):
            if not jadwal1.schedule or not jadwal2.schedule:
                return JsonResponse({'status': 'error', 'message': f'Data jadwal ID: {jadwal1.id}/ID: {jadwal2.id} Anda tidak ditemukan. Hubungi Admin.'})

            sudah_masuk = InAbsences.objects.filter(
                nik=user,
                date_in__range=(start_of_day, end_of_day),
                date_in__isnull=False,
            ).exists()

            if sudah_masuk:
                print(f'Semua shift sudah absen')
                return JsonResponse({
                    'status': 'error',
                    'message': f'{user.name}, Anda sudah absen pulang untuk semua shift hari ini.'
                })

            sched = jadwal1.schedule

            jadwal_in_today = timezone.make_aware(
                datetime.combine(today, sched.start_time),
                tz_jakarta
            )

            status_in = "Tepat Waktu" if now <= jadwal_in_today else "Terlambat"

            request.session["pending_absence"] = {
                "mode": "MASUK_LONG",
                "user_id": user.nik,
                "today": today.isoformat(),
                "shifts": [
                    {
                        "schedule_id": jadwal1.schedule.id,
                        "shift_order": jadwal1.shift_order,
                        "status_in": status_in,
                        "planned_out": jadwal1.schedule.end_time.isoformat()
                    },
                    {
                        "schedule_id": jadwal2.schedule.id,
                        "shift_order": jadwal2.shift_order,
                        "planned_in": jadwal2.schedule.start_time.isoformat()
                    }
                ],
                "actual_in": now.isoformat()
            }

            return JsonResponse({
                "status": "success",
                "type": "Masuk (Long Shift)",
                "shift": f"{jadwal1.shift_order}-{jadwal2.shift_order}",
                "message": (
                    f"Tanggal <b>{today}</b> shift "
                    f"<b>{jadwal1.schedule.start_time} - {jadwal2.schedule.end_time}</b>"
                ),
                "status_absen": status_in,
                "nik": user.nik,
                "name": user.name,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "minor_message": "Semangat bekerja 💪🏼"
            })


        # =====================================================
        # NORMAL SHIFT (ABSEN PER SHIFT)
        # =====================================================
        for jadwal in jadwal_list:
            sudah_masuk = InAbsences.objects.filter(
                nik=user,
                shift_order=jadwal.shift_order,
                date_in__range=(start_of_day, end_of_day),
            ).exists()

            if not sudah_masuk:
                sched = jadwal.schedule

                if not sched:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Data jadwal ID: {jadwal.id} tidak ditemukan. Hubungi Admin.'
                    })

                jadwal_in_today = timezone.make_aware(
                    datetime.combine(today, sched.start_time),
                    tz_jakarta
                )

                print(now, jadwal_in_today)

                status_in = "Tepat Waktu" if now <= jadwal_in_today else "Terlambat"

                request.session["pending_absence"] = {
                    "mode": "MASUK",
                    "user_id": user.nik,
                    "schedule_id": sched.id,
                    "shift_order": jadwal.shift_order,
                    "status_in": status_in,
                    "time": now.isoformat()
                }

                return JsonResponse({
                    "status": "success",
                    "type": "Masuk",
                    "shift": jadwal.shift_order,
                    "message": (
                        f"Tanggal <b>{jadwal.date}</b> shift "
                        f"<b>{sched.start_time} - {sched.end_time}</b>"
                    ),
                    "status_absen": status_in,
                    "nik": user.nik,
                    "name": user.name,
                    "date": now.strftime('%Y-%m-%d'),
                    "time": now.strftime('%H:%M:%S'),
                    "minor_message": "Semangat bekerja 💪🏼"
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

def confirm_absence(request):
    from django.utils import timezone
    from datetime import time

    action = request.POST.get("action")
    temp = request.session.get("pending_absence")

    if not temp:
        return JsonResponse({"status": "error", "message": "Data tidak ditemukan"})

    if action == "no":
        del request.session["pending_absence"]
        return JsonResponse({"status": "cancelled"})

    if action != "yes":
        return JsonResponse({"status": "error", "message": "Aksi tidak valid"})

    now = timezone.localtime(timezone.now())
    today = now.date()
    tz_jakarta = pytz.timezone('Asia/Jakarta')
    start_of_day = timezone.make_aware(datetime.combine(today, time.min), tz_jakarta)
    end_of_day = timezone.make_aware(datetime.combine(today, time.max), tz_jakarta)

    # =====================================================
    # ABSEN MASUK NORMAL
    # =====================================================
    if temp["mode"] == "MASUK":
        InAbsences.objects.create(
            nik_id=temp["user_id"],
            date_in=temp["time"],
            status_in=temp["status_in"],
            schedule_id=temp["schedule_id"],
            shift_order=temp["shift_order"]
        )

    # =====================================================
    # ABSEN MASUK LONG SHIFT
    # =====================================================
    elif temp["mode"] == "MASUK_LONG":
        actual_in = datetime.fromisoformat(temp["actual_in"])

        for shift in temp["shifts"]:
            schedule = MasterSchedules.objects.get(id=shift["schedule_id"])

            # shift 1
            if "planned_out" in shift:
                planned_out = datetime.combine(today, schedule.end_time)

                InAbsences.objects.create(
                    nik_id=temp["user_id"],
                    schedule=schedule,
                    shift_order=shift["shift_order"],
                    date_in=actual_in,
                    date_out=planned_out,
                    status_in=shift["status_in"],
                    status_out=None
                )

            # shift 2
            if "planned_in" in shift:
                planned_in = datetime.combine(today, schedule.start_time)

                InAbsences.objects.create(
                    nik_id=temp["user_id"],
                    schedule=schedule,
                    shift_order=shift["shift_order"],
                    date_in=planned_in,
                    status_in="Tepat Waktu"
                )

    # =====================================================
    # ABSEN PULANG NORMAL
    # =====================================================
    elif temp["mode"] == "PULANG":
        absen = InAbsences.objects.get(id=temp["absence_id"])
        absen.date_out = temp["time"]
        absen.status_out = temp["status_out"]
        absen.save()

    # =====================================================
    # ABSEN PULANG LONG SHIFT
    # =====================================================
    elif temp["mode"] == "PULANG_LONG": 
        from django.db import transaction 
        
        now_aware = timezone.localtime(timezone.now())
        
        with transaction.atomic(): 
            absens = list(
                InAbsences.objects
                .select_for_update()
                .filter(
                    nik_id=temp["user_id"],
                    status_out__isnull=True
                    # date_in__gte=now - timedelta(hours=24)
                )
                .select_related("schedule")
                .order_by("shift_order")
            )

            if len(absens) < 2: 
                return JsonResponse({ "status": "error", "message": "Data shift long tidak lengkap" })
            
            shift1, shift2 = absens[0], absens[1] 

            print(f'Shift1 ID: {shift1.id}, Shift2 ID: {shift2.id}')
            sched1, sched2 = shift1.schedule, shift2.schedule

            date_in_day1 = shift1.date_in.date()
            date_in_day2 = shift2.date_in.date()
            
            end1 = timezone.make_aware(datetime.combine(date_in_day1, sched1.end_time), tz_jakarta)
            end2 = timezone.make_aware(datetime.combine(date_in_day2, sched2.end_time), tz_jakarta)
            shift1datein = timezone.localtime(shift1.date_in)
            print(f'end1: {end1}, {shift1datein}')
            
            if end1 <= timezone.localtime(shift1.date_in): 
                end1 += timedelta(days=1) 
            if end2 <= timezone.localtime(shift2.date_in): 
                end2 += timedelta(days=1) 

            print(f'end1: {end1}, end2: {end2}, now: {now_aware}')
                
            if now_aware < end1: 
                # KASUS 1: Pulang Cepat di Shift 1
                shift1.date_out = now_aware 
                shift1.status_out = "Pulang Cepat" 
                shift1.save() 
                shift2.delete()
                
            elif now_aware < end2: 
                # KASUS 2: Pulang di tengah Shift 2
                shift1.date_out = end1
                shift1.status_out = "Tepat Waktu" 
                shift1.save() 
                
                shift2.date_out = now_aware 
                shift2.status_out = "Pulang Cepat" 
                shift2.save() 
                
            else: 
                # KASUS 3: Pulang Tepat Waktu (Setelah Shift 2 Selesai)
                shift1.date_out = end1
                shift1.status_out = "Tepat Waktu" 
                shift1.save() 
                
                shift2.date_out = now_aware 
                shift2.status_out = "Tepat Waktu" 
                shift2.save()

    else:
        return JsonResponse({"status": "error", "message": "Mode absensi tidak dikenal"})

    del request.session["pending_absence"]

    message = (
        "Semangat bekerja 💪🏼"
        if "MASUK" in temp["mode"]
        else "Hati-hati di jalan 🛵"
    )

    return JsonResponse({
        "status": "success",
        "minor_message": message
    })

def overtime(request):
    if request.method != 'POST':
        return render(request, 'user/absence.html')

    try:
        # 1. Ambil & Validasi Input
        photo_data = request.POST.get('photo')
        if not photo_data:
            return JsonResponse({'status': 'error', 'message': 'Foto tidak ditemukan'})

        # 2. Decode Base64
        img_bytes, ext = decode_base64_image(photo_data)
        if not img_bytes:
            return JsonResponse({'status': 'error', 'message': 'Format foto tidak valid'})

        # 3. Ambil Encoding dari Foto Upload
        uploaded_enc, error_msg = extract_face_encoding(img_bytes, ext)
        if error_msg:
            return JsonResponse({'status': 'error', 'message': error_msg})

        # 4. Ambil Data Wajah Terdaftar (Cache/DB)
        known_encodings, user_list = get_known_faces_from_cache(Users)
        if not known_encodings:
            return JsonResponse({'status': 'error', 'message': 'Tidak ada data wajah terdaftar'})

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

        if not user:
            return JsonResponse({"status": "error", "message": "Wajah tidak dikenali"})

        # 2. CEK LEMBUR AKTIF
        active_ot = Overtimes.objects.filter(
            nik=user,
            end_date__isnull=True
        ).first()

        # ======================
        # PULANG LEMBUR
        # ======================
        if active_ot:
            duration_minutes = int((now - active_ot.start_date).total_seconds() // 60)
            request.session["pending_overtime"] = {
                "mode": "PULANG",
                "overtime_id": active_ot.id,
                "duration_minutes": duration_minutes,
                "time": now.isoformat()
            }

            #duration_minutes on HH:MM:ss format
            duration_minutes_hours = duration_minutes // 60
            duration_minutes_remainder = duration_minutes % 60
            duration_minutes = f"{duration_minutes_hours} jam {duration_minutes_remainder} menit"

            return JsonResponse({
                "status": "success",
                "type": "Pulang Lembur",
                "shift": "-",
                "message": f"Tanggal <b>{active_ot.start_date.date()}</b>. Total <b>{duration_minutes}</b>",
                "status_absen": 'Draft',
                "nik": user.nik,
                "name": user.name,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime("%H:%M:%S"),
                "minor_message": "Semangat bekerja 💪🏼"
            })
        
        # ======================
        # MASUK LEMBUR
        # ======================
        sedang_kerja = InAbsences.objects.filter(
            nik=user,
            date_out__isnull=True
        )

        if sedang_kerja.exists():
            return JsonResponse({
                "status": "error",
                "message": f"{user.name}, status Anda 'Sedang Bekerja'. Silakan absen pulang terlebih dahulu, jika ingin mengajukan lembur."
            })
        
        request.session["pending_overtime"] = {
            "mode": "MASUK",
            "user_id": user.nik,
            "time": now.isoformat(),
            "date": today.isoformat()
        }

        return JsonResponse({
            "status": "success",
            "type": "Masuk Lembur",
            "shift": "-",
            "message": f"Tanggal <b>{now.strftime('%Y-%m-%d')}</b>",
            "status_absen": 'Draft',
            "nik": user.nik,
            "name": user.name,
            "date": now.strftime('%Y-%m-%d'),
            "time": now.strftime("%H:%M:%S"),
            "minor_message": "Semangat bekerja 💪🏼"
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error: {str(e)}'
        })
    
def confirm_overtime(request):
    from django.utils import timezone

    action = request.POST.get("action")
    temp = request.session.get("pending_overtime")

    if not temp:
        return JsonResponse({"status": "error", "message": "Data tidak ditemukan"})

    if action == "no":
        del request.session["pending_overtime"]
        return JsonResponse({"status": "cancelled"})

    now = timezone.localtime()

    if temp["mode"] == "MASUK":
        Overtimes.objects.create(
            nik_id=temp["user_id"],
            overtime_date=temp["date"],
            start_date=temp["time"],
            status="DRAFT"
        )

    elif temp["mode"] == "PULANG":
        ot = Overtimes.objects.get(id=temp["overtime_id"])
        ot.end_date = temp["time"]
        ot.duration_minutes = temp["duration_minutes"]
        ot.save()

    else:
        return JsonResponse({"status": "error", "message": "Mode tidak dikenal"})

    del request.session["pending_overtime"]

    message = (
        "Semangat lembur 💪🏼 😭"
        if "MASUK" in temp["mode"]
        else "Hati-hati di jalan 🛵 🥲"
    )

    return JsonResponse({
        "status": "success",
        "minor_message": message
    })

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

        new_leave_request.save()
        # if photo_file:
        #     new_leave_request.photo = photo_file

        # new_leave_request.save()

        messages.success(request, 'Pengajuan cuti berhasil diupload.')
        return redirect('/users/pengajuan_cuti')

    cuti_list = MasterLeaves.objects.all()
    boss_list = Users.objects.filter(is_admin__in=[1,2]).exclude(nik=user.nik)
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
            pengajuan.status = 'Pending'
            pengajuan.user_target = boss_obj


            # if(photo_file):
            #    pengajuan.photo = photo_file

            pengajuan.save() 

            messages.success(request, 'Data perubahan pengajuan cuti berhasil diupload.')
            return redirect('/users/pengajuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal mengupload perubahan data pengajuan cuti. Error: {e}')
            return redirect('/users/pengajuan_cuti')

    boss_list = Users.objects.filter(is_admin__in=[1,2]).exclude(nik=user.nik)

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
        'boss_list': Users.objects.filter(is_admin__in=[1, 2]).exclude(nik=user.nik),
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
        pengajuan.status = 'Pending'
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
        'boss_list': Users.objects.filter(is_admin__in=[1, 2]).exclude(nik=user.nik),
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


@login_auth
def keluar_bentar(request):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    from django.utils import timezone
    today = timezone.localdate()

    active_out = OutPermission.objects.filter(
        nik=user.nik,
        date=today,
        status='Keluar'
    ).first()

    if request.method == 'POST':

        if active_out:
            messages.error(request, 'Anda masih dalam status izin keluar.')
            return redirect('keluar_bentar')

        reason = request.POST.get('reason')
        if not reason:
            messages.error(request, 'Alasan wajib diisi.')
            return redirect('keluar_bentar')

        OutPermission.objects.create(
            nik=user,
            date=today,
            time_out=timezone.now(),
            reason=reason,
            status='Keluar'
        )

        messages.success(request, 'Izin keluar berhasil dicatat.')
        return redirect('keluar_bentar')

    start_date = today - timedelta(days=30)

    today_permissions = OutPermission.objects.filter(
        nik=user,
        date__range=(start_date, today)
    ).order_by('-date', '-time_out')

    context = {
        'user': user,
        'active_out': active_out,
        'today_permissions': today_permissions,
        'today': today
    }

    return render(request, 'user/keluar/keluar_bentar.html', context)

@login_auth
def balik_keluar_bentar(request):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    from django.utils import timezone
    today = timezone.localdate()

    active_out = OutPermission.objects.filter(
        nik=user,
        date=today,
        status='Keluar'
    ).first()

    if not active_out:
        messages.error(request, 'Tidak ada izin keluar yang aktif.')
        return redirect('keluar_bentar')

    time_in = timezone.now()
    duration = int((time_in - active_out.time_out).total_seconds() / 60)

    active_out.time_in = time_in
    active_out.duration_minutes = duration
    active_out.status = 'Kembali'
    active_out.save()

    messages.success(
        request,
        f'Kembali bekerja berhasil. Durasi izin: {duration} menit.'
    )

    return redirect('keluar_bentar')

def timedelta_to_hms(td):
    if not td:
        return "00:00:00"

    total_seconds = int(td.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@login_auth
def pengajuan_lembur(request):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    lembur_list = Overtimes.objects.filter(status='DRAFT').order_by('-overtime_date')
    done_lembur_list = Overtimes.objects.filter(status__in=['SUBMITTED', 'DIVISI APPROVED', 'APPROVED', 'REJECTED']).order_by('-overtime_date')

    for lembur in lembur_list:
        second = lembur.duration_minutes * 60 if lembur.end_date != None else 0
        total_jam = timedelta_to_hms(timedelta(seconds=second))
        lembur.total_jam = total_jam

    for lembur in done_lembur_list:
        second = lembur.duration_minutes * 60 if lembur.end_date != None else 0
        total_jam = timedelta_to_hms(timedelta(seconds=second))
        lembur.total_jam = total_jam

    context = {
        'user': user,
        'lembur_list': lembur_list,
        'done_lembur_list': done_lembur_list,
        'title': 'Pengajuan Lembur'
    }

    return render(request, 'user/lembur/index.html', context)

@login_auth
def detail_pengajuan_lembur(request, id):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))

    if request.method == 'POST':
        approved_by = request.POST.get('approved_by')
        reason = request.POST.get('reason')

        lembur = get_object_or_404(Overtimes, id=id)

        if approved_by and reason:
            boss_obj = get_object_or_404(Users, nik=approved_by)
            lembur.approved_by = boss_obj
            lembur.reason = reason
            lembur.status = 'SUBMITTED'
            lembur.save()
            messages.success(request, 'Pengajuan lembur berhasil diperbarui.')
        else:
            messages.error(request, 'Pengajuan lembur gagal diperbarui.')

        return redirect('/users/pengajuan_lembur')

    lembur = get_object_or_404(Overtimes, id=id)
    boss_list = Users.objects.filter(is_admin__in=[1,2]).exclude(nik=user.nik)

    second = lembur.duration_minutes * 60
    total_jam = timedelta_to_hms(timedelta(seconds=second))
    lembur.total_jam = total_jam

    context = {
        'user': user,
        'lembur': lembur,
        'boss_list': boss_list,
        'title': 'Detail Pengajuan Lembur'
    }

    return render(request, 'user/lembur/detail.html', context)
