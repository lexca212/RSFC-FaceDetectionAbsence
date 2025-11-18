from django.core.files.storage import default_storage
from django.core.files.base import ContentFile  
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import render
from django.utils import timezone
import face_recognition
from .models import *
import base64

# Create your views here.

def absence(request):
    if request.method == 'POST':
        photo_data = request.POST.get('photo')

        if not photo_data:
            return JsonResponse({'status': 'error', 'message': 'Foto tidak valid'})

        # Decode base64 photo
        format, imgstr = photo_data.split(';base64,')
        ext = format.split('/')[-1]
        photo_data = ContentFile(base64.b64decode(imgstr), name=f'temp_photo.{ext}')

        try:
            # Process the uploaded base64 photo
            img_data = base64.b64decode(imgstr)
            temp_file_name = f'temp_photo.{ext}'
            temp_file_path = default_storage.save(temp_file_name, ContentFile(img_data))
            temp_file_full_path = default_storage.path(temp_file_path)

            # Load the uploaded photo
            uploaded_image = face_recognition.load_image_file(temp_file_full_path)
            uploaded_encoding = face_recognition.face_encodings(uploaded_image)

            if len(uploaded_encoding) == 0:
                default_storage.delete(temp_file_path)
                return JsonResponse({'status': 'error', 'message': 'Tidak dapat mengenali wajah pada foto yang diunggah'})

            uploaded_encoding = uploaded_encoding[0]

            # Loop through all user and compare faces
            all_user = Users.objects.all()
            for user in all_user:
                user_photo_path = user.photo.path
                user_photo = face_recognition.load_image_file(user_photo_path)
                user_encoding = face_recognition.face_encodings(user_photo)

                if len(user_encoding) == 0:
                    continue  
                user_encoding = user_encoding[0]

                # Compare the uploaded photo with the database photo
                results = face_recognition.compare_faces([user_encoding], uploaded_encoding, tolerance=0.4)

                date = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

                if results[0]:
                    InAbsences.objects.create(
                        nik=user,           
                        date=date,
                        status='present'
                    )
                    default_storage.delete(temp_file_path)
                    messages.success(request, 'Berhasil Absen')
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Berhasil Absen',
                        'nik': user.nik,
                        'name': user.name,
                        'date': date
                    })

            default_storage.delete(temp_file_path)
            return JsonResponse({'status': 'error', 'message': 'Wajah tidak cocok dengan data manapun'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Gagal memproses absensi: {e}'})

    return render(request, 'user/absence.html')