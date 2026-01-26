from django.db import models
from utils.image import compress_image

# Create your models here.
class Users(models.Model):
    nik = models.CharField(max_length=20, unique=True, primary_key=True)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='img/')
    divisi = models.CharField(max_length=100,null=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=100)
    face_encoding = models.BinaryField(null=True, blank=True)
    is_admin = models.IntegerField(choices=[
        (0, 'User'),
        (1, 'Admin'),
        (2, 'Super User')
    ],
    default=0
)
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
    shift_order = models.PositiveSmallIntegerField(null=True, blank=True)
    is_from_leave = models.BooleanField(default=False)
    leave_request = models.ForeignKey(
        'cms.LeaveRequests',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    is_from_permission = models.BooleanField(default=False)
    permission_request = models.ForeignKey(
        'app.PermissionRequests',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class OutAbsences(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey(Users, on_delete=models.CASCADE)
    date = models.DateTimeField()
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class PermissionRequests(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    permission_type = models.ForeignKey('cms.MasterPermission', on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='bukti_izin/', null=True, blank=True)
    note = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')
    user_target = models.ForeignKey('app.Users', related_name='permission_approver', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.photo:
            self.photo = compress_image(self.photo)
        super().save(*args, **kwargs)

class OutPermission(models.Model):
    nik = models.ForeignKey('app.Users', on_delete=models.CASCADE)

    date = models.DateField()
    time_out = models.DateTimeField()
    time_in = models.DateTimeField(null=True, blank=True)

    duration_minutes = models.IntegerField(null=True, blank=True)

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=[
            ('OUT', 'Sedang Keluar'),
            ('RETURN', 'Sudah Kembali'),
            ('CANCEL', 'Dibatalkan'),
        ],
        default='OUT'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Overtimes(models.Model):
    id = models.AutoField(primary_key=True)
    nik = models.ForeignKey(Users,on_delete=models.CASCADE,related_name="overtimes")
    overtime_date = models.DateField()
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("DRAFT", "Draft"),
            ("SUBMITTED", "Submitted"),
            ("DIVISI APPROVED", "Divisi Approved"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
        default="DRAFT"
    )
    approved_by = models.ForeignKey(Users,null=True,blank=True,on_delete=models.SET_NULL, related_name="approved_overtimes")
    approved_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
