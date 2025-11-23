from django.core.files.storage import default_storage
from django.core.files.base import ContentFile  
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.shortcuts import render
from cms.models import *
import face_recognition
from .models import *
import base64

# Create your views here.

def absence(request):
    if request.method == 'POST':
        photo_data = request.POST.get('photo')

        if not photo_data:
            return JsonResponse({'status': 'error', 'message': 'Foto tidak valid'})

        # Decode base64
        format, imgstr = photo_data.split(';base64,')
        ext = format.split('/')[-1]
        img_bytes = base64.b64decode(imgstr)

        temp_name = f'temp_photo.{ext}'
        temp_path = default_storage.save(temp_name, ContentFile(img_bytes))
        temp_full = default_storage.path(temp_path)

        try:
            uploaded_img = face_recognition.load_image_file(temp_full)
            uploaded_enc = face_recognition.face_encodings(uploaded_img)

            if len(uploaded_enc) == 0:
                default_storage.delete(temp_path)
                return JsonResponse({'status': 'error', 'message': 'Wajah tidak terdeteksi (Mungkin Kurang Tengah)'})

            uploaded_enc = uploaded_enc[0]

            # Loop user
            all_user = Users.objects.all()
            now = datetime.now()
            today = now.date()

            for user in all_user:
                user_img = face_recognition.load_image_file(user.photo.path)
                user_enc = face_recognition.face_encodings(user_img)

                if len(user_enc) == 0:
                    continue

                user_enc = user_enc[0]
                match = face_recognition.compare_faces([user_enc], uploaded_enc, tolerance=0.45)

                # Jika wajah cocok
                if match[0]:
                    # ===================================================== 
                    # CEK SUDAH IN DAN OUT (TIDAK BOLEH ABSEN 3 KALI) 
                    # ===================================================== 
                    already_done = InAbsences.objects.filter( 
                        nik=user, 
                        date_in__date=today, 
                        date_out__isnull=False 
                    ).first()
                    
                    if already_done:
                        if already_done.schedule.name == 'Libur':
                             default_storage.delete(temp_path) 
                             return JsonResponse({ 'status': 'error', 'message': 'Tidak ada jadwal untuk hari ini. Libur... Boss' })
                        
                        default_storage.delete(temp_path) 
                        return JsonResponse({ 'status': 'error', 'message': 'Anda kan sudah absen pulang hari ini...' })

                    # =====================================================
                    # CEK APAKAH SUDAH ADA ABSEN IN YANG BELUM OUT
                    # =====================================================
                    existing_absen = InAbsences.objects.filter(
                        nik=user,
                        date_out__isnull=True
                    ).order_by('-date_in').first()

                    # =====================================================
                    # JIKA ADA ABSEN IN → LAKUKAN ABSEN OUT
                    # =====================================================
                    if existing_absen:
                        schedule_in = existing_absen.schedule
                        date_in_day = existing_absen.date_in.date()

                        jadwal_in = datetime.combine(date_in_day, schedule_in.start_time)
                        jadwal_out = datetime.combine(date_in_day, schedule_in.end_time)

                        if jadwal_out < jadwal_in:
                            jadwal_out += timedelta(days=1)

                        if now < jadwal_out:
                            status_out = "Pulang Cepat"
                        else:
                            status_out = "Tepat Waktu"

                        existing_absen.date_out = now
                        existing_absen.status_out = status_out
                        existing_absen.save()

                        default_storage.delete(temp_path)
                        return JsonResponse({
                            'status': 'success',
                            'type': 'Keluar',
                            'message': f'Absen keluar berhasil',
                            'status_absen': status_out,
                            'nik': user.nik,
                            'name': user.name,
                            'date': now.strftime('%Y-%m-%d'),
                            'time': now.strftime('%H:%M:%S'),
                            'minor_message': 'Hati-hati di Jalan 🛵'
                        })

                    # =====================================================
                    # TIDAK ADA ABSEN IN → LAKUKAN ABSEN IN
                    # =====================================================
                    schedule_today = MappingSchedules.objects.filter(
                        nik=user,
                        date=today
                    ).first()

                    # print(f'{schedule_today.schedule.name}')

                    if not schedule_today or schedule_today.schedule.name == "Libur":
                        default_storage.delete(temp_path)
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Tidak ada jadwal untuk hari ini. Libur... Boss'
                        })

                    schedule_master = schedule_today.schedule

                    jadwal_in_today = datetime.combine(today, schedule_master.start_time)

                    if now <= jadwal_in_today:
                        status_in = "Tepat Waktu"
                    else:
                        status_in = "Terlambat"

                    InAbsences.objects.create(
                        nik=user,
                        date_in=now,
                        status_in=status_in,
                        schedule=schedule_master 
                    )

                    default_storage.delete(temp_path)
                    return JsonResponse({
                        'status': 'success',
                        'type': 'Masuk',
                        'message': f'Absen masuk berhasil',
                        'status_absen': status_in,
                        'nik': user.nik,
                        'name': user.name,
                        'date': now.strftime('%Y-%m-%d'),
                        'time': now.strftime('%H:%M:%S'),
                        'minor_message': 'Semangat Bekerja 💪🏼'
                    })

            # Jika wajah tidak ditemukan
            default_storage.delete(temp_path)
            return JsonResponse({'status': 'error', 'message': 'Wajah Anda tidak terdaftar. Daftarkan dulu !!!'})

        except Exception as e:
            default_storage.delete(temp_path)
            return JsonResponse({'status': 'error', 'message': f'Error: {e}'})
        
    return render(request, 'user/absence.html')


