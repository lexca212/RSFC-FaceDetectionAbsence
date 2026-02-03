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
    shift_order = models.PositiveSmallIntegerField(null=True, blank=True)
    is_from_leave = models.BooleanField(default=False)
    original_schedule = models.ForeignKey(
        MasterSchedules,
        null=True,
        blank=True,
        related_name='original_schedule',
        on_delete=models.SET_NULL
    )
    is_from_permission = models.BooleanField(default=False)
    original_schedule_permission = models.ForeignKey(
        MasterSchedules,
        null=True, blank=True,
        related_name='permission_original_schedule',
        on_delete=models.SET_NULL
    )
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
    status = models.CharField(max_length=20, default='Pending')
    user_target = models.ForeignKey('app.Users', related_name='approver', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MasterPermission(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    max_days = models.IntegerField()
    is_requires_attachment = models.BooleanField(default=False)
    max_per_month = models.IntegerField(null=True, blank=True)

class FCMToken(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)