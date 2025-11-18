from django.shortcuts import redirect
from functools import wraps

def login_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Periksa apakah 'nik_id' ada di sesi
        if 'nik_id' in request.session:
            return view_func(request, *args, **kwargs)
        else:
            # Jika tidak ada, alihkan ke halaman login Anda
            return redirect('/admins/login') 
    return wrapper