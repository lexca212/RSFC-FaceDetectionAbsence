from django.db import models

# Create your models here.
class SalaryComponent(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=[
        ('earning', 'Earning'),
        ('deduction', 'Deduction')
    ])
    calculation_type = models.CharField(
        max_length=20,
        choices=[
        ('fixed', 'Fixed'),
        ('per_day', 'Per Day'),
        ('per_hour', 'Per Hour'),
        ('overtime', 'Overtime'),
        ('per_minute', 'Per Minute'),
        ('percentage', 'Percentage')
    ])
    is_active = models.BooleanField(default=True)


class UserSalaryComponent(models.Model):
    user = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_start = models.DateField()
    effective_end = models.DateField(null=True, blank=True)

# class WorkDaySummary(models.Model):
#     user = models.ForeignKey('app.Users', on_delete=models.CASCADE)
#     date = models.DateField()
#     scheduled_hours = models.FloatField()
#     actual_hours = models.FloatField()
#     overtime_hours = models.FloatField()
#     late_minutes = models.IntegerField()
#     status = models.CharField(choices=[
#         ('present', 'Present'),
#         ('leave', 'Leave'),
#         ('absent', 'Absent'),
#         ('off', 'Off')
#     ])


class Payroll(models.Model):
    user = models.ForeignKey('app.Users', on_delete=models.CASCADE)
    period_start = models.DateField()
    period_end = models.DateField()
    total_earning = models.DecimalField(max_digits=14, decimal_places=2)
    total_deduction = models.DecimalField(max_digits=14, decimal_places=2)
    net_salary = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
        ('draft', 'Draft'),
        ('final', 'Final')
    ])
    generated_at = models.DateTimeField(auto_now_add=True)


class PayrollDetail(models.Model):
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE)
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
