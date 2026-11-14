from pathlib import Path

path = Path("backend/app/api/routes/allocations.py")

if not path.exists():
    print("Allocation route file not found:", path)
    raise SystemExit(1)

content = path.read_text(encoding="utf-8-sig")

if 'router.get("/overview")' in content:
    print("Overview endpoint already exists. No changes made.")
    raise SystemExit(0)

addition = '''

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
'''

path.write_text(content + addition, encoding="utf-8")
print("SUCCESS: Allocation overview endpoint added.")
