from pathlib import Path
import re

path = Path("backend/app/api/routes/resources.py")
content = path.read_text(encoding="utf-8-sig")

# Ensure ExamSession is imported.
if "ExamSession" not in content.split("router =")[0]:
    content = content.replace(
        "from backend.app.models import Resource, Allocation, Examination",
        "from backend.app.models import Resource, Allocation, Examination, ExamSession"
    )

replacement = '''

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

'''

pattern = r'@router\.delete\("/all"\).*?(?=@router\.get\("/\{resource_id\}")'

updated, count = re.subn(
    pattern,
    replacement + "\n",
    content,
    count=1,
    flags=re.S
)

if count != 1:
    print("ERROR: Reset endpoint was not replaced. No file changes saved.")
    raise SystemExit(1)

path.write_text(updated, encoding="utf-8")
print("SUCCESS: Reset endpoint updated with correct deletion order.")
