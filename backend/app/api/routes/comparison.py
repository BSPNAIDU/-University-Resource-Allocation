
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import (
    Examination,
    Resource,
    ExamRegistration,
    Student,
)
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university
from backend.app.optimizer.comparison import compare_algorithms

router = APIRouter(
    prefix="/api/v1/optimization",
    tags=["Algorithm Comparison"],
)


@router.get("/compare/{examination_id}")
def compare_examination_algorithms(
    examination_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    # Get examination belonging to the logged-in university.
    examination = (
        db.query(Examination)
        .filter(
            Examination.id == examination_id,
            Examination.university_id == university.id,
        )
        .first()
    )

    if examination is None:
        raise HTTPException(
            status_code=404,
            detail="Examination not found.",
        )

    # Get only this university's registered students.
    registrations = (
        db.query(ExamRegistration)
        .join(Student)
        .options(joinedload(ExamRegistration.student))
        .filter(
            ExamRegistration.university_id == university.id,
            ExamRegistration.examination_id == examination_id,
            Student.university_id == university.id,
            ExamRegistration.registration_status == "registered",
            Student.is_active.is_(True),
        )
        .order_by(Student.student_number)
        .all()
    )

    students = [
        registration.student
        for registration in registrations
    ]

    if not students:
        raise HTTPException(
            status_code=400,
            detail="No active registered students found.",
        )

    # Get only this university's available rooms.
    rooms = (
        db.query(Resource)
        .filter(
            Resource.university_id == university.id,
            Resource.is_available.is_(True),
        )
        .order_by(Resource.room_number)
        .all()
    )

    if not rooms:
        raise HTTPException(
            status_code=400,
            detail="No available rooms found.",
        )

    # Compare algorithms without modifying database allocations.
    result = compare_algorithms(students, rooms)

    return {
        "message": "Algorithm comparison completed successfully.",
        "university": university.university_name,
        "examination": {
            "id": examination.id,
            "exam_code": examination.exam_code,
            "subject_name": examination.subject_name,
            "department": examination.department,
            "exam_date": str(examination.exam_date),
            "registered_students": len(students),
        },
        "available_rooms": len(rooms),
        "comparison": result["comparison"],
        "recommended_algorithm": result["recommended_algorithm"],
        "selection_criteria": result["selection_criteria"],
        "database_modified": False,
    }
