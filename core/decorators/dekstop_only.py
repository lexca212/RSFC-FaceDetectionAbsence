from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def desktop_only(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        ua = request.user_agent

        if ua.is_mobile or ua.is_tablet:
            messages.error(request, "Anda tidak memiliki akses ke halaman ini.")
            return redirect('/admins/dekstop_only403')

        return view_func(request, *args, **kwargs)

    return _wrapped_view
