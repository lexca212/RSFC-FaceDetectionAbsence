from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from cms.models import *
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from app.models import *
from .models import *
from .decorators import session_check

# Create your views here.
    
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        if not email or not password:
            messages.error(request, 'email and password are required')
            return redirect('/payroll/login')

        user = Users.objects.filter(email=email).first()

        if user is None:
            messages.error(request, 'Your email is not registerd')
            return redirect('/payroll/login')

        if not check_password(password, user.password):
            messages.error(request, 'Your password is invalid')
            return redirect('/payroll/login')

        request.session['nik_id'] = user.nik
        request.session['is_admin'] = user.is_admin
        request.session['is_accountant'] = user.is_accountant

        if user.is_accountant == 1:
            return redirect('/payroll/dashboard')
        else:
            messages.error(request, 'You are not authorized to access this system')
            return redirect('/payroll/login')
        
    return render(request, 'payroll/login.html')

@session_check
def dashboard(request):
    user = Users.objects.filter(nik=request.session['nik_id']).first()

    context = {
        'user': user
    }

    return render(request, 'payroll/dashboard.html', context)

@session_check
def komponen_gaji(request):
    user = Users.objects.filter(nik=request.session['nik_id']).first()

    salery_components = SalaryComponent.objects.all()

    context = {
        'user': user,
        'salery_components': salery_components
    }

    return render(request, 'payroll/komponen_gaji/index.html', context)

@session_check
def add_komponen_gaji(request):
    if request.method == 'POST':
        name = request.POST['name']
        type = request.POST['type']
        calculation_type = request.POST['calculation_type']

        if not name or not type or not calculation_type:
            messages.error(request, 'All fields are required')
            return redirect('/payroll/komponen_gaji/add/')

        SalaryComponent.objects.create(
            name=name,
            type=type,
            calculation_type=calculation_type,
            is_active=True
        )

        messages.success(request, 'Salary component added successfully')
        return redirect('/payroll/komponen_gaji/')
    
    user = Users.objects.filter(nik=request.session['nik_id']).first()

    calculation_types = [
        ('Tetap', 'Tetap'),
        ('Per Hari', 'Per Hari'),
        ('Per Jam', 'Per Jam'),
        ('Per Menit', 'Per Menit'),
        ('Lembur', 'Lembur'),
        ('Persentase', 'Persentase')
    ]

    context = {
        'user': user,
        'title': 'Tambah Komponen Gaji',
        'calculation_types': calculation_types
    }
    return render(request, 'payroll/komponen_gaji/add.html', context)
    
@session_check
def edit_komponen_gaji(request, id):
    component = SalaryComponent.objects.filter(id=id).first()

    if request.method == 'POST':
        name = request.POST['name']
        type = request.POST['type']
        calculation_type = request.POST['calculation_type']
        status = request.POST.get('is_active', 'off')

        if not name or not type or not calculation_type:
            messages.error(request, 'All fields are required')
            return redirect(f'/payroll/komponen_gaji/edit/{id}/')

        component.name = name
        component.type = type
        component.calculation_type = calculation_type
        component.is_active = True if status == 'on' else False
        component.save()

        messages.success(request, 'Salary component updated successfully')
        return redirect('/payroll/komponen_gaji/')
    
    user = Users.objects.filter(nik=request.session['nik_id']).first()

    calculation_types = [
        ('Tetap', 'Tetap'),
        ('Per Hari', 'Per Hari'),
        ('Per Jam', 'Per Jam'),
        ('Per Menit', 'Per Menit'),
        ('Lembur', 'Lembur'),
        ('Persentase', 'Persentase')
    ]

    context = {
        'user': user,
        'title': 'Edit Komponen Gaji',
        'component': component,
        'calculation_types': calculation_types
    }
    return render(request, 'payroll/komponen_gaji/edit.html', context)

@session_check
def delete_komponen_gaji(request, id):
    component = SalaryComponent.objects.filter(id=id).first()

    if component:
        component.delete()
        messages.success(request, 'Salary component deleted successfully')
    else:
        messages.error(request, 'Salary component not found')

    return redirect('/payroll/komponen_gaji/')

@session_check
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

    return render(request, 'payroll/komponen_gaji_karyawan/index.html', context)

@session_check
def detail_gaji(request, nik):
    user = get_object_or_404(Users, nik=request.session.get('nik_id'))
    karyawan = get_object_or_404(Users, nik=nik)

    if request.method == "POST":
        action = request.POST.get("action")
        record_id = request.POST.get("record_id")

        print(request.POST.get("component_id"), request.POST.get("amount"), request.POST.get("start"), request.POST.get("end"))

        if action == "create":
            UserSalaryComponent.objects.create(
                nik=karyawan,
                component_id=request.POST.get("component_id"),
                amount=request.POST.get("amount"),
                effective_start=request.POST.get("start"),
                effective_end=request.POST.get("end") or None
            )
            messages.success(request, "Data berhasil ditambahkan")

        elif action == "update" and record_id:
            obj = UserSalaryComponent.objects.get(id=record_id)
            obj.component_id = request.POST.get("component_id")
            obj.amount = request.POST.get("amount")
            obj.effective_start = request.POST.get("start")
            obj.effective_end = request.POST.get("end") or None
            obj.save()
            messages.success(request, "Data berhasil diupdate")

        elif action == "delete" and record_id:
            UserSalaryComponent.objects.get(id=record_id).delete()
            messages.success(request, "Data berhasil dihapus")

        return redirect(request.path)

    components = SalaryComponent.objects.filter(is_active=True).all()
    user_components = UserSalaryComponent.objects.filter(nik=karyawan).select_related('component').all()
    divisi = MasterDivisions.objects.filter(id=karyawan.divisi).first()
    karyawan.divisi = divisi

    context = {
        'user': user,
        'title': 'Detail Gaji Karyawan',
        'karyawan': karyawan,
        'components': components,
        'user_components': user_components,
    }

    return render(request, 'payroll/komponen_gaji_karyawan/detail.html', context)