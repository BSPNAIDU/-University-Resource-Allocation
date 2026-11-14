
from datetime import datetime, timedelta


def get_exam_times(examination):
    start = datetime.combine(
        examination.exam_date,
        examination.start_time
    )

    end = start + timedelta(
        minutes=examination.duration_minutes
    )

    return start, end


def exams_overlap(exam_one, exam_two):
    if exam_one.exam_date != exam_two.exam_date:
        return False

    start_one, end_one = get_exam_times(exam_one)
    start_two, end_two = get_exam_times(exam_two)

    return start_one < end_two and start_two < end_one


def detect_student_conflicts(examinations, registrations):
    conflicts = []

    registration_map = {}

    for registration in registrations:
        if registration.registration_status != "registered":
            continue

        registration_map.setdefault(
            registration.student_id, []
        ).append(registration.examination_id)

    examination_map = {
        examination.id: examination
        for examination in examinations
    }

    for student_id, examination_ids in registration_map.items():
        for first_index in range(len(examination_ids)):
            for second_index in range(first_index + 1, len(examination_ids)):
                first_exam = examination_map.get(
                    examination_ids[first_index]
                )
                second_exam = examination_map.get(
                    examination_ids[second_index]
                )

                if first_exam is None or second_exam is None:
                    continue

                if exams_overlap(first_exam, second_exam):
                    conflicts.append({
                        "student_id": student_id,
                        "first_examination_id": first_exam.id,
                        "first_exam_code": first_exam.exam_code,
                        "second_examination_id": second_exam.id,
                        "second_exam_code": second_exam.exam_code,
                        "conflict_type": "student_schedule_conflict",
                    })

    return conflicts


def detect_room_conflicts(examinations, allocations):
    conflicts = []

    examination_map = {
        examination.id: examination
        for examination in examinations
    }

    room_map = {}

    for allocation in allocations:
        if allocation.allocation_status not in [
            "allocated",
            "reallocated",
        ]:
            continue

        room_map.setdefault(
            allocation.resource_id, {}
        ).setdefault(
            allocation.examination_id, []
        ).append(allocation)

    for room_id, room_examinations in room_map.items():
        examination_ids = list(room_examinations.keys())

        for first_index in range(len(examination_ids)):
            for second_index in range(first_index + 1, len(examination_ids)):
                first_exam = examination_map.get(
                    examination_ids[first_index]
                )
                second_exam = examination_map.get(
                    examination_ids[second_index]
                )

                if first_exam is None or second_exam is None:
                    continue

                if exams_overlap(first_exam, second_exam):
                    conflicts.append({
                        "resource_id": room_id,
                        "first_examination_id": first_exam.id,
                        "first_exam_code": first_exam.exam_code,
                        "second_examination_id": second_exam.id,
                        "second_exam_code": second_exam.exam_code,
                        "conflict_type": "room_schedule_conflict",
                    })

    return conflicts


def filter_rooms_without_schedule_conflicts(db, examination, rooms):
    """
    Exclude rooms already allocated to overlapping examinations
    belonging to the same university.
    Does not modify existing allocations.
    """
    from backend.app.models import Allocation, Examination

    if not rooms:
        return []

    room_ids = [room.id for room in rooms]

    existing_bookings = (
        db.query(
            Allocation.resource_id,
            Examination.start_time,
            Examination.duration_minutes
        )
        .join(
            Examination,
            Allocation.examination_id == Examination.id,
        )
        .filter(
            Allocation.university_id == examination.university_id,
            Examination.university_id == examination.university_id,
            Allocation.resource_id.in_(room_ids),
            Allocation.examination_id != examination.id,
            Allocation.allocation_status.in_(
                ["allocated", "reallocated"]
            ),
            Examination.exam_date == examination.exam_date,
        )
        .all()
    )

    current_start, current_end = get_exam_times(examination)
    busy_room_ids = set()

    for room_id, start_time, duration in existing_bookings:
        existing_start = datetime.combine(
            examination.exam_date, start_time
        )

        existing_end = existing_start + timedelta(
            minutes=duration
        )

        if current_start < existing_end and existing_start < current_end:
            busy_room_ids.add(room_id)

    return [
        room for room in rooms
        if room.id not in busy_room_ids
    ]
