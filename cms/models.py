from django.db import models

# Create your models here.
class MasterDivisions(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MasterSchedules(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MappingSchedules(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    nik = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    schedule = models.ForeignKey(MasterSchedules, on_delete=models.CASCADE)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MasterLeaves(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    default_quota = models.IntegerField(default=0)  
    auto_days = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LeaveRequests(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(MasterLeaves, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='static/cuti_img', null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
