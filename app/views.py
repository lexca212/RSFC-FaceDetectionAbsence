from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile  
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.contrib import messages
from cms.decorators import login_auth
from datetime import date, datetime
from cms.models import *
import face_recognition
from .models import *
import calendar
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
                        status = already_done.schedule.name

                        messages = {
                            'Libur': 'Tidak ada jadwal untuk hari ini. Libur... Boss',
                            'Cuti': 'Tidak ada jadwal untuk hari ini. Katanya mau cuti !!'
                        }

                        message = messages.get(status, 'Anda kan sudah absen pulang hari ini...')

                        default_storage.delete(temp_path)

                        return JsonResponse({
                            'status': 'error',
                            'message': message
                        })
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

@login_auth
def pengajuan_cuti(request):
    user = get_object_or_404(Users, nik=request.session['nik_id'])

    if request.method == 'POST':
        leave_type_id = request.POST['cuti']
        leave_type_obj = get_object_or_404(MasterLeaves, id=leave_type_id)
        photo_file = request.FILES.get('photo') 
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        reason = request.POST['reason']

        try:
            new_leave_request = LeaveRequests(
                nik=user,
                leave_type=leave_type_obj,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
            )
            
            if photo_file:
                new_leave_request.photo = photo_file 
            
            new_leave_request.save()

            messages.success(request, 'Data pengajuan cuti berhasil diupload.')
            return redirect('pengajuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal mengupload data pengajuan cuti. Error: {e}')
            return redirect('pengajuan_cuti')

    cuti_list = MasterLeaves.objects.all()

    pengajuan_list = LeaveRequests.objects.filter(
        nik_id = user.nik
    )
            
    context = {
       'user': user,
       'cuti_list':cuti_list,
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
        photo_file = request.FILES.get('photo') 
        start_date = request.POST['start_date']
        end_date = request.POST['end_date']
        reason = request.POST['reason']

        try:
            pengajuan = get_object_or_404(LeaveRequests, id=id)

            pengajuan.leave_type =  leave_type_obj
            pengajuan.start_date = start_date
            pengajuan.end_date = end_date
            pengajuan.reason = reason

            if(photo_file):
               pengajuan.photo = photo_file

            pengajuan.save() 

            messages.success(request, 'Data perubahan pengajuan cuti berhasil diupload.')
            return redirect('pengajuan_cuti') 
            
        except Exception as e:
            messages.error(request, f'Gagal mengupload perubahan data pengajuan cuti. Error: {e}')
            return redirect('pengajuan_cuti')

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
            return redirect('profile', nik=detail_user.nik)
        
        except Exception as e:
            messages.error(request, f'Gagal mengupdate data Anda: {e}')
            
            return redirect('profile', nik=detail_user.nik) 

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
        'title': 'Profile ' + detail_user.name
    }

    return render(request, 'user/profile/index.html', context)