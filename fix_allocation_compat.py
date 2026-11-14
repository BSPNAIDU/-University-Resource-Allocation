from pathlib import Path

path = Path("backend/app/api/routes/allocations.py")
content = path.read_text(encoding="utf-8-sig")

if 'def list_allocations_by_examination(' in content:
    print("Compatibility endpoint already exists.")
    raise SystemExit(0)

endpoint = '''

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
'''

path.write_text(content.rstrip() + endpoint + "\\n", encoding="utf-8")
print("SUCCESS: Examination allocation compatibility endpoint added.")
