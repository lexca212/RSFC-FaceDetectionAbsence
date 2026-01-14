from datetime import datetime, timedelta
from app.models import InAbsences
from cms.models import MappingSchedules, MasterSchedules

def apply_leave(pengajuan):
    start = pengajuan.start_date
    end = pengajuan.end_date

    cuti_schedule, _ = MasterSchedules.objects.get_or_create(
        id="CUTI",
        defaults={"name": "Cuti", "start_time": "00:00", "end_time": "00:00"}
    )

    current = start
    while current <= end:

        # === MAPPING SCHEDULE ===
        mapping = MappingSchedules.objects.filter(
            nik=pengajuan.nik,
            date=current
        ).first()

        if mapping:
            if not mapping.is_from_leave:
                mapping.original_schedule = mapping.schedule
                mapping.schedule = cuti_schedule
                mapping.is_from_leave = True
                mapping.save()
        else:
            MappingSchedules.objects.create(
                id=f"{pengajuan.nik.nik}_{current}",
                nik=pengajuan.nik,
                schedule=cuti_schedule,
                original_schedule=None,
                is_from_leave=True,
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
                "status_in": "Cuti",
                "status_out": "Cuti",
                "schedule": cuti_schedule,
                "shift_order": 1,
                "is_from_leave": True,
                "leave_request": pengajuan
            }
        )

        current += timedelta(days=1)


def revert_leave(pengajuan):
    start = pengajuan.start_date
    end = pengajuan.end_date

    # === RESTORE SCHEDULE ===
    schedules = MappingSchedules.objects.filter(
        nik=pengajuan.nik,
        date__range=(start, end),
        is_from_leave=True
    )

    for s in schedules:
        if s.original_schedule:
            s.schedule = s.original_schedule
            s.original_schedule = None
            s.is_from_leave = False
            s.save()
        else:
            s.delete()

    # === DELETE ABSENCE ===
    InAbsences.objects.filter(
        nik=pengajuan.nik,
        leave_request=pengajuan,
        is_from_leave=True
    ).delete()
