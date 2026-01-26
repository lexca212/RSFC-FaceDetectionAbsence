from datetime import datetime, timedelta
from app.models import InAbsences
from cms.models import MappingSchedules, MasterSchedules

def apply_permission(pengajuan):
    start = pengajuan.start_date
    end = pengajuan.end_date

    izin_schedule, _ = MasterSchedules.objects.get_or_create(
        id="IZIN",
        defaults={"name": "Izin", "start_time": "00:00", "end_time": "00:00"}
    )

    current = start
    while current <= end:

        # === MAPPING SCHEDULE ===
        mapping = MappingSchedules.objects.filter(
            nik=pengajuan.nik,
            date=current
        ).first()

        if mapping:
            if not mapping.is_from_permission:
                mapping.original_schedule = mapping.schedule
                mapping.schedule = izin_schedule
                mapping.is_from_permission = True
                mapping.save()
        else:
            MappingSchedules.objects.create(
                id=f"{pengajuan.nik.nik}_{current}",
                nik=pengajuan.nik,
                schedule=izin_schedule,
                original_schedule=None,
                is_from_permission=True,
                date=current,
                shift_order=1
            )

        # === IN ABSENCE ===
        InAbsences.objects.update_or_create(
            nik=pengajuan.nik,
            date_in__date=current,
            defaults={
                "date_in": datetime.combine(current, datetime.min.time()),
                "date_out": datetime.combine(current, datetime.max.time()),
                "status_in": "Izin",
                "status_out": "Izin",
                "schedule": izin_schedule,
                "shift_order": 1,
                "is_from_permission": True,
                "permission_request": pengajuan
            }
        )

        current += timedelta(days=1)

def revert_permission(pengajuan):
    start = pengajuan.start_date
    end = pengajuan.end_date

    # === RESTORE SCHEDULE ===
    schedules = MappingSchedules.objects.filter(
        nik=pengajuan.nik,
        date__range=(start, end),
        is_from_permission=True
    )

    for s in schedules:
        if s.original_schedule:
            s.schedule = s.original_schedule
            s.original_schedule = None
            s.is_from_permission = False
            s.save()
        else:
            s.delete()

    # === DELETE ABSENCE ===
    InAbsences.objects.filter(
        nik=pengajuan.nik,
        permission_request=pengajuan,
        is_from_permission=True
    ).delete()
