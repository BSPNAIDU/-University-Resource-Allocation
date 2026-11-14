from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import (
    Student, Resource, Examination, Allocation,
    ExamRegistration, ExamSession
)
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university
from backend.app.optimizer.greedy import greedy_allocate

router = APIRouter(
    prefix="/api/v1/allocations",
    tags=["Allocations"],
)


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    sessions = (
        db.query(ExamSession)
        .filter(ExamSession.university_id == university.id)
        .order_by(ExamSession.exam_date, ExamSession.start_time)
        .all()
    )

    result = []

    for session in sessions:
        exam = db.query(Examination).filter(
            Examination.id == session.examination_id,
            Examination.university_id == university.id,
        ).first()

        registered = db.query(ExamRegistration).filter(
            ExamRegistration.session_id == session.id,
            ExamRegistration.university_id == university.id,
            ExamRegistration.registration_status == "registered",
        ).count()

        allocated = db.query(Allocation).filter(
            Allocation.session_id == session.id,
            Allocation.university_id == university.id,
        ).count()

        result.append({
            "id": session.id,
            "session_id": session.id,
            "examination_id": exam.id if exam else None,
            "exam_code": exam.exam_code if exam else "",
            "subject_name": exam.subject_name if exam else "",
            "session_name": session.session_name,
            "exam_date": str(session.exam_date),
            "start_time": str(session.start_time),
            "duration_minutes": session.duration_minutes,
            "capacity": session.capacity,
            "registered_students": registered,
            "allocated_students": allocated,
        })

    return result


@router.post("/generate-session/{session_id}")
def generate_session_allocations(
    session_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    session = db.query(ExamSession).filter(
        ExamSession.id == session_id,
        ExamSession.university_id == university.id,
    ).first()

    if session is None:
        raise HTTPException(404, "Exam session not found.")

    examination = db.query(Examination).filter(
        Examination.id == session.examination_id,
        Examination.university_id == university.id,
    ).first()

    if examination is None:
        raise HTTPException(404, "Examination not found.")

    existing_count = db.query(Allocation).filter(
        Allocation.session_id == session.id,
        Allocation.university_id == university.id,
    ).count()

    if existing_count:
        raise HTTPException(
            409,
            "Allocations already exist for this session."
        )

    registrations = (
        db.query(ExamRegistration)
        .join(Student, ExamRegistration.student_id == Student.id)
        .options(joinedload(ExamRegistration.student))
        .filter(
            ExamRegistration.session_id == session.id,
            ExamRegistration.examination_id == examination.id,
            ExamRegistration.university_id == university.id,
            ExamRegistration.registration_status == "registered",
            Student.is_active.is_(True),
        )
        .order_by(Student.student_number)
        .all()
    )

    students = [registration.student for registration in registrations]

    if not students:
        raise HTTPException(
            400,
            "No registered students are assigned to this session."
        )

    if len(students) > session.capacity:
        raise HTTPException(
            400,
            f"Session capacity exceeded. Capacity: {session.capacity}; "
            f"registered students: {len(students)}."
        )

    rooms = db.query(Resource).filter(
        Resource.university_id == university.id,
        Resource.is_available.is_(True),
    ).order_by(Resource.room_number).all()

    try:
        proposed = greedy_allocate(students, rooms)
    except ValueError as error:
        raise HTTPException(400, str(error))

    if len(proposed) != len(students):
        raise HTTPException(
            400,
            f"Insufficient room capacity. Required: {len(students)}; "
            f"available: {len(proposed)}."
        )

    try:
        saved = []

        for item in proposed:
            saved.append(
                Allocation(
                    university_id=university.id,
                    student_id=item["student_id"],
                    examination_id=examination.id,
                    session_id=session.id,
                    resource_id=item["resource_id"],
                    seat_number=item["seat_number"],
                    allocation_status="allocated",
                )
            )

        db.add_all(saved)
        db.commit()

        return {
            "message": "Session seating allocation completed.",
            "session_id": session.id,
            "session_name": session.session_name,
            "exam_code": examination.exam_code,
            "total_students": len(students),
            "total_rooms_used": len({
                item["resource_id"] for item in proposed
            }),
        }

    except Exception as error:
        db.rollback()
        raise HTTPException(
            500,
            f"Allocation failed. Changes rolled back: {error}"
        )


@router.get("/session/{session_id}")
def get_session_allocations(
    session_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    session = db.query(ExamSession).filter(
        ExamSession.id == session_id,
        ExamSession.university_id == university.id,
    ).first()

    if session is None:
        raise HTTPException(404, "Exam session not found.")

    allocations = db.query(Allocation).options(
        joinedload(Allocation.student),
        joinedload(Allocation.resource),
    ).filter(
        Allocation.session_id == session.id,
        Allocation.university_id == university.id,
    ).order_by(
        Allocation.resource_id,
        Allocation.seat_number,
    ).all()

    return {
        "session_id": session.id,
        "session_name": session.session_name,
        "total_allocations": len(allocations),
        "allocations": [
            {
                "allocation_id": item.id,
                "student_number": item.student.student_number,
                "student_name": item.student.full_name,
                "room_number": item.resource.room_number,
                "seat_number": item.seat_number,
                "status": item.allocation_status,
            }
            for item in allocations
        ],
    }


@router.get("/overview")
def allocation_overview(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    from backend.app.models import (
        Student, Examination, ExamSession, Resource, Allocation
    )

    total_students = db.query(Student).filter(
        Student.university_id == university.id,
        Student.is_active.is_(True)
    ).count()

    total_examinations = db.query(Examination).filter(
        Examination.university_id == university.id
    ).count()

    total_sessions = db.query(ExamSession).filter(
        ExamSession.university_id == university.id
    ).count()

    total_rooms = db.query(Resource).filter(
        Resource.university_id == university.id
    ).count()

    total_allocations = db.query(Allocation).filter(
        Allocation.university_id == university.id,
        Allocation.allocation_status == "allocated"
    ).count()

    return {
        "total_students": total_students,
        "total_examinations": total_examinations,
        "total_sessions": total_sessions,
        "total_rooms": total_rooms,
        "total_allocations": total_allocations,
        "unallocated_students": max(0, total_students - total_allocations)
    }

# Backward-compatible endpoint used by the existing Streamlit page.
@router.get("/{examination_id}")
def list_allocations_by_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    examination = db.query(Examination).filter(
        Examination.id == examination_id,
        Examination.university_id == university.id,
    ).first()

    if examination is None:
        raise HTTPException(404, "Examination not found.")

    allocations = db.query(Allocation).options(
        joinedload(Allocation.student),
        joinedload(Allocation.resource),
        joinedload(Allocation.session),
    ).filter(
        Allocation.examination_id == examination_id,
        Allocation.university_id == university.id,
    ).order_by(
        Allocation.session_id,
        Allocation.resource_id,
        Allocation.seat_number,
    ).all()

    return {
        "examination_id": examination.id,
        "exam_code": examination.exam_code,
        "subject_name": examination.subject_name,
        "total_allocations": len(allocations),
        "allocations": [
            {
                "allocation_id": item.id,
                "student_id": item.student_id,
                "student_name": item.student.full_name,
                "room_number": item.resource.room_number,
                "seat_number": item.seat_number,
                "session_id": item.session_id,
                "exam_date": item.session.exam_date.isoformat(),
                "start_time": item.session.start_time.isoformat(),
                "status": item.allocation_status,
            }
            for item in allocations
        ],
    }
