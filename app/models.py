from django.db import models

# Create your models here.
class Users(models.Model):
    nik = models.CharField(max_length=20, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='static/img')
    divisi = models.CharField(max_length=100,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Admins(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    is_superadmin = models.BooleanField(default=False)
    nik = models.ForeignKey(Users, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class InAbsences(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey(Users, on_delete=models.CASCADE)
    date_in = models.DateTimeField()
    status_in = models.CharField(max_length=20)
    date_out = models.DateTimeField(null=True, blank=True)
    status_out = models.CharField(max_length=20, null=True, blank=True)
    schedule = models.ForeignKey('cms.MasterSchedules', null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OutAbsences(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey(Users, on_delete=models.CASCADE)
    date = models.DateTimeField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
