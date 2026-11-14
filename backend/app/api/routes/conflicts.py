from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import (
    Examination,
    ExamRegistration,
    Allocation,
)
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university

from backend.app.optimizer.conflict_detection import (
    detect_student_conflicts,
    detect_room_conflicts,
)

router = APIRouter(
    prefix="/api/v1/conflicts",
    tags=["Conflict Detection"],
)


@router.get("/")
def detect_all_conflicts(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    # Fetch only this university's examinations.
    examinations = (
        db.query(Examination)
        .filter(Examination.university_id == university.id)
        .all()
    )

    # Fetch only this university's registrations.
    registrations = (
        db.query(ExamRegistration)
        .filter(
            ExamRegistration.university_id == university.id,
            ExamRegistration.registration_status == "registered",
        )
        .all()
    )

    # Fetch only this university's active allocations.
    allocations = (
        db.query(Allocation)
        .filter(
            Allocation.university_id == university.id,
            Allocation.allocation_status.in_([
                "allocated",
                "reallocated",
            ]),
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

    total_conflicts = (
        len(student_conflicts) + len(room_conflicts)
    )

    return {
        "message": "Conflict detection completed successfully.",
        "university": university.university_name,
        "total_examinations_checked": len(examinations),
        "student_conflict_count": len(student_conflicts),
        "room_conflict_count": len(room_conflicts),
        "total_conflicts": total_conflicts,
        "status": (
            "conflicts_found"
            if total_conflicts > 0
            else "no_conflicts"
        ),
        "student_conflicts": student_conflicts,
        "room_conflicts": room_conflicts,
    }
