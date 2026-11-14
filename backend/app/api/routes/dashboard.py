from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    Student,
    Resource,
    Examination,
    Allocation,
    ExamRegistration,
)
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university

from backend.app.optimizer.conflict_detection import (
    detect_student_conflicts,
    detect_room_conflicts,
)

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard Analytics"],
)


@router.get("/")
def get_dashboard_analytics(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    # University-specific record counts
    total_students = (
        db.query(Student)
        .filter(Student.university_id == university.id)
        .count()
    )

    total_examinations = (
        db.query(Examination)
        .filter(Examination.university_id == university.id)
        .count()
    )

    total_rooms = (
        db.query(Resource)
        .filter(Resource.university_id == university.id)
        .count()
    )

    available_rooms = (
        db.query(Resource)
        .filter(
            Resource.university_id == university.id,
            Resource.is_available.is_(True),
        )
        .count()
    )

    unavailable_rooms = total_rooms - available_rooms

    total_allocations = (
        db.query(Allocation)
        .filter(
            Allocation.university_id == university.id,
            Allocation.allocation_status.in_(
                ["allocated", "reallocated"]
            ),
        )
        .count()
    )

    total_registrations = (
        db.query(ExamRegistration)
        .filter(
            ExamRegistration.university_id == university.id,
            ExamRegistration.registration_status == "registered",
        )
        .count()
    )

    allocation_percentage = (
        round((total_allocations / total_registrations) * 100, 2)
        if total_registrations > 0
        else 0
    )

    # Fetch university-specific records for conflict detection.
    examinations = (
        db.query(Examination)
        .filter(Examination.university_id == university.id)
        .all()
    )

    registrations = (
        db.query(ExamRegistration)
        .filter(
            ExamRegistration.university_id == university.id,
            ExamRegistration.registration_status == "registered",
        )
        .all()
    )

    allocations = (
        db.query(Allocation)
        .filter(
            Allocation.university_id == university.id,
            Allocation.allocation_status.in_(
                ["allocated", "reallocated"]
            ),
        )
        .all()
    )

    student_conflicts = detect_student_conflicts(
        examinations,
        registrations,
    )

    room_conflicts = detect_room_conflicts(
        examinations,
        allocations,
    )

    student_conflict_count = len(student_conflicts)
    room_conflict_count = len(room_conflicts)

    total_conflicts = (
        student_conflict_count + room_conflict_count
    )

    # Examination distribution by department.
    department_distribution = (
        db.query(
            Examination.department,
        )
        .filter(Examination.university_id == university.id)
        .all()
    )

    department_counts = {}

    for item in department_distribution:
        department = item[0]
        department_counts[department] = (
            department_counts.get(department, 0) + 1
        )

    # Latest examination schedule.
    recent_examinations = (
        db.query(Examination)
        .filter(Examination.university_id == university.id)
        .order_by(
            Examination.exam_date.desc(),
            Examination.start_time.desc(),
        )
        .limit(10)
        .all()
    )

    return {
        "university": {
            "id": university.id,
            "name": university.university_name,
            "code": university.university_code,
        },
        "overview": {
            "total_students": total_students,
            "total_examinations": total_examinations,
            "total_rooms": total_rooms,
            "total_allocations": total_allocations,
            "total_registrations": total_registrations,
            "allocation_percentage": allocation_percentage,
        },
        "room_statistics": {
            "available_rooms": available_rooms,
            "unavailable_rooms": unavailable_rooms,
        },
        "conflict_statistics": {
            "student_conflict_count": student_conflict_count,
            "room_conflict_count": room_conflict_count,
            "total_conflicts": total_conflicts,
            "status": (
                "conflicts_found"
                if total_conflicts > 0
                else "no_conflicts"
            ),
            "student_conflicts": student_conflicts,
            "room_conflicts": room_conflicts,
        },
        "department_distribution": department_counts,
        "recent_examinations": [
            {
                "id": exam.id,
                "exam_code": exam.exam_code,
                "subject_name": exam.subject_name,
                "department": exam.department,
                "exam_date": str(exam.exam_date),
                "start_time": str(exam.start_time),
                "duration_minutes": exam.duration_minutes,
                "student_count": exam.student_count,
            }
            for exam in recent_examinations
        ],
    }
