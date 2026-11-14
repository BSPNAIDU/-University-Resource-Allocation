from backend.app.models import Student
from backend.app.models import ExamRegistration

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from backend.app.database import get_db
from backend.app.models import Resource, Allocation, Examination, ExamSession, ResourceDateAvailability
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university
from backend.app.optimizer.conflict_detection import (
    filter_rooms_without_schedule_conflicts,
)

router = APIRouter(prefix="/api/v1/resources", tags=["Resources"])


class ResourceCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=30)
    building: str = Field(min_length=1, max_length=100)
    capacity: int = Field(ge=1)
    is_available: bool = True
    room_type: str = Field(default="Examination Hall", max_length=50)


class ResourceBulkCreate(BaseModel):
    rooms: list[ResourceCreate] = Field(min_length=1, max_length=200)


class ResourceUpdate(BaseModel):
    is_available: bool
    exam_date: date


class ResourceResponse(BaseModel):
    id: int
    room_number: str
    building: str
    capacity: int
    is_available: bool
    room_type: str

    model_config = {"from_attributes": True}


def get_university_room(
    db: Session,
    resource_id: int,
    university_id: int,
):
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.university_id == university_id,
    ).first()

    if resource is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    return resource


@router.post(
    "/bulk",
    response_model=list[ResourceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_resources_bulk(
    bulk_data: ResourceBulkCreate,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    room_keys = [
        (room.building.strip().casefold(), room.room_number.strip().casefold())
        for room in bulk_data.rooms
    ]

    if len(room_keys) != len(set(room_keys)):
        raise HTTPException(
            status_code=409,
            detail="Duplicate room numbers found within the submitted blocks.",
        )

    existing_rooms = db.query(Resource).filter(
        Resource.university_id == university.id
    ).all()

    existing_keys = {
        (room.building.strip().casefold(), room.room_number.strip().casefold())
        for room in existing_rooms
    }

    new_room_data = [
        room for room, key in zip(bulk_data.rooms, room_keys)
        if key not in existing_keys
    ]

    if not new_room_data:
        return []

    try:
        new_rooms = [
            Resource(
                university_id=university.id,
                room_number=room.room_number.strip(),
                building=room.building.strip(),
                capacity=room.capacity,
                is_available=room.is_available,
                room_type=room.room_type,
            )
            for room in new_room_data
        ]

        db.add_all(new_rooms)
        db.flush()

        response_data = [
            ResourceResponse.model_validate(room)
            for room in new_rooms
        ]

        db.commit()
        return response_data

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Room setup failed. Database transaction rolled back: {error}",
        )


@router.post(
    "/",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_resource(
    resource_data: ResourceCreate,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    existing = db.query(Resource).filter(
        Resource.university_id == university.id,
        Resource.building.ilike(resource_data.building.strip()),
        Resource.room_number.ilike(resource_data.room_number.strip()),
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This room number already exists in this building.",
        )

    try:
        resource = Resource(
            university_id=university.id,
            **resource_data.model_dump(),
        )

        resource.room_number = resource.room_number.strip()
        resource.building = resource.building.strip()

        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Room creation failed.",
        )


@router.get("/", response_model=list[ResourceResponse])
def list_resources(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    return (
        db.query(Resource)
        .filter(Resource.university_id == university.id)
        .order_by(Resource.id)
        .all()
    )


@router.get("/available", response_model=list[ResourceResponse])
def list_available_resources(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    return (
        db.query(Resource)
        .filter(
            Resource.university_id == university.id,
            Resource.is_available.is_(True),
        )
        .order_by(Resource.room_number)
        .all()
    )




@router.delete("/all")
def delete_all_university_resources(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    university_id = university.id

    try:
        # Count records before deletion.
        allocation_count = db.query(Allocation).filter(
            Allocation.university_id == university_id
        ).count()

        registration_count = db.query(ExamRegistration).filter(
            ExamRegistration.university_id == university_id
        ).count()

        session_count = db.query(ExamSession).filter(
            ExamSession.university_id == university_id
        ).count()

        examination_count = db.query(Examination).filter(
            Examination.university_id == university_id
        ).count()

        student_count = db.query(Student).filter(
            Student.university_id == university_id
        ).count()

        room_count = db.query(Resource).filter(
            Resource.university_id == university_id
        ).count()

        # Delete child records before parent records.
        db.query(Allocation).filter(
            Allocation.university_id == university_id
        ).delete(synchronize_session=False)

        db.query(ExamRegistration).filter(
            ExamRegistration.university_id == university_id
        ).delete(synchronize_session=False)

        db.query(ExamSession).filter(
            ExamSession.university_id == university_id
        ).delete(synchronize_session=False)

        db.query(Examination).filter(
            Examination.university_id == university_id
        ).delete(synchronize_session=False)

        db.query(Student).filter(
            Student.university_id == university_id
        ).delete(synchronize_session=False)

        db.query(Resource).filter(
            Resource.university_id == university_id
        ).delete(synchronize_session=False)

        # University accounts and other universities remain untouched.
        db.commit()

        return {
            "message": "University testing data reset successfully.",
            "university_id": university_id,
            "deleted_allocations": allocation_count,
            "deleted_registrations": registration_count,
            "deleted_sessions": session_count,
            "deleted_examinations": examination_count,
            "deleted_students": student_count,
            "deleted_classrooms": room_count
        }

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"University reset failed. All changes rolled back: {str(error)}"
        )


@router.get("/{resource_id}", response_model=ResourceResponse)
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    return get_university_room(db, resource_id, university.id)


@router.put("/{resource_id}")
def update_resource(
    resource_id: int,
    resource_data: ResourceUpdate,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    """
    Set availability for one room on one examination date.
    The Resource.is_available flag remains the university-wide master status.
    """
    resource = db.query(Resource).filter(
        Resource.id == resource_id,
        Resource.university_id == university.id,
    ).with_for_update().first()

    if resource is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    exam_date = resource_data.exam_date

    try:
        date_status = db.query(ResourceDateAvailability).filter(
            ResourceDateAvailability.university_id == university.id,
            ResourceDateAvailability.resource_id == resource.id,
            ResourceDateAvailability.exam_date == exam_date,
        ).with_for_update().first()

        if resource_data.is_available:
            if date_status is not None:
                db.delete(date_status)
            db.commit()
            return {
                "message": f"{resource.room_number} is available on {exam_date}.",
                "room": ResourceResponse.model_validate(resource),
                "exam_date": exam_date.isoformat(),
                "reallocation": None,
            }

        if date_status is not None and date_status.is_available is False:
            return {
                "message": f"{resource.room_number} is already unavailable on {exam_date}.",
                "room": ResourceResponse.model_validate(resource),
                "exam_date": exam_date.isoformat(),
                "reallocation": None,
            }

        if date_status is None:
            date_status = ResourceDateAvailability(
                university_id=university.id,
                resource_id=resource.id,
                exam_date=exam_date,
                is_available=False,
            )
            db.add(date_status)
        else:
            date_status.is_available = False
        db.flush()

        affected_allocations = (
            db.query(Allocation)
            .join(ExamSession, Allocation.session_id == ExamSession.id)
            .options(joinedload(Allocation.student))
            .filter(
                Allocation.university_id == university.id,
                Allocation.resource_id == resource.id,
                Allocation.allocation_status.in_(["allocated", "reallocated"]),
                ExamSession.university_id == university.id,
                ExamSession.exam_date == exam_date,
            )
            .order_by(Allocation.session_id, Allocation.student_id)
            .all()
        )

        affected_by_session = defaultdict(list)
        for allocation in affected_allocations:
            affected_by_session[allocation.session_id].append(allocation)

        details = []
        total_reallocated = 0

        for session_id, old_allocations in affected_by_session.items():
            session = db.query(ExamSession).filter(
                ExamSession.id == session_id,
                ExamSession.university_id == university.id,
            ).first()

            if session is None:
                raise HTTPException(status_code=409, detail=f"Session {session_id} not found.")

            examination = db.query(Examination).filter(
                Examination.id == session.examination_id,
                Examination.university_id == university.id,
            ).first()

            if examination is None:
                raise HTTPException(status_code=409, detail=f"Examination for session {session_id} not found.")

            blocked_room_ids = db.query(ResourceDateAvailability.resource_id).filter(
                ResourceDateAvailability.university_id == university.id,
                ResourceDateAvailability.exam_date == exam_date,
                ResourceDateAvailability.is_available.is_(False),
            )

            available_rooms = db.query(Resource).filter(
                Resource.university_id == university.id,
                Resource.is_available.is_(True),
                Resource.capacity > 0,
                ~Resource.id.in_(blocked_room_ids),
            ).order_by(Resource.building, Resource.room_number).all()

            current_start = datetime.combine(session.exam_date, session.start_time)
            current_end = current_start + timedelta(minutes=session.duration_minutes)

            room_ids = [room.id for room in available_rooms]
            busy_room_ids = set()
            if room_ids:
                bookings = (
                    db.query(Allocation.resource_id, ExamSession)
                    .join(ExamSession, Allocation.session_id == ExamSession.id)
                    .filter(
                        Allocation.university_id == university.id,
                        ExamSession.university_id == university.id,
                        Allocation.resource_id.in_(room_ids),
                        Allocation.session_id != session.id,
                        Allocation.allocation_status.in_(["allocated", "reallocated"]),
                        ExamSession.exam_date == exam_date,
                    ).all()
                )
                for room_id, other_session in bookings:
                    other_start = datetime.combine(other_session.exam_date, other_session.start_time)
                    other_end = other_start + timedelta(minutes=other_session.duration_minutes)
                    if current_start < other_end and other_start < current_end:
                        busy_room_ids.add(room_id)

            suitable_rooms = [room for room in available_rooms if room.id not in busy_room_ids]

            affected_ids = [item.id for item in old_allocations]
            unaffected = db.query(Allocation).filter(
                Allocation.university_id == university.id,
                Allocation.session_id == session.id,
                Allocation.id.notin_(affected_ids),
                Allocation.allocation_status.in_(["allocated", "reallocated"]),
            ).all()

            occupied = defaultdict(set)
            for item in unaffected:
                occupied[item.resource_id].add(item.seat_number)

            proposed = []
            for room in suitable_rooms:
                for seat_index in range(1, room.capacity + 1):
                    seat_number = f"S{seat_index:02d}"
                    if seat_number not in occupied[room.id]:
                        proposed.append((room.id, seat_number))
                        if len(proposed) == len(old_allocations):
                            break
                if len(proposed) == len(old_allocations):
                    break

            if len(proposed) < len(old_allocations):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Insufficient free seats on {exam_date} for session "
                        f"{session.session_name}. Required {len(old_allocations)}, "
                        f"available {len(proposed)}. Nothing was changed."
                    ),
                )

            old_values = [
                (item.student_id, item.examination_id)
                for item in old_allocations
            ]
            for item in old_allocations:
                db.delete(item)
            db.flush()

            for (student_id, examination_id), (room_id, seat_number) in zip(old_values, proposed):
                db.add(Allocation(
                    university_id=university.id,
                    student_id=student_id,
                    examination_id=examination_id,
                    session_id=session.id,
                    resource_id=room_id,
                    seat_number=seat_number,
                    allocation_status="reallocated",
                ))

            total_reallocated += len(old_allocations)
            details.append({
                "session_id": session.id,
                "session_name": session.session_name,
                "exam_code": examination.exam_code,
                "affected_students": len(old_allocations),
                "reallocated_students": len(old_allocations),
            })

        db.commit()
        db.refresh(resource)
        return {
            "message": f"{resource.room_number} marked unavailable on {exam_date}; only sessions on this date were processed.",
            "room": ResourceResponse.model_validate(resource),
            "exam_date": exam_date.isoformat(),
            "reallocation": {
                "affected_students": len(affected_allocations),
                "reallocated_students": total_reallocated,
                "sessions_affected": len(details),
                "details": details,
            },
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Date-specific reallocation failed; all changes rolled back: {error}",
        )
