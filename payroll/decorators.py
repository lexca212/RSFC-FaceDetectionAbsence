from django.shortcuts import redirect
from django.contrib import messages

def session_check(view_func):
    def wrapper(request, *args, **kwargs):
        if 'nik_id' not in request.session:
            messages.error(request, 'Anda harus login terlebih dahulu')
            return redirect('/payroll/login')
        if request.session.get('is_accountant') != 1:
            messages.error(request, 'Akun Anda tidak memiliki akses ke aplikasi ini')
            return redirect('/payroll/login')
        return view_func(request, *args, **kwargs)
    return wrapper