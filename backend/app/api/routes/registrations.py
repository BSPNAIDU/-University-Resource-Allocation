from io import BytesIO
import re

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_university
from backend.app.models import (
    Student, Examination, ExamRegistration, ExamSession
)
from backend.app.models.university import University

router = APIRouter(
    prefix="/api/v1/registrations",
    tags=["Subject Registrations"]
)


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


@router.post("/upload")
async def upload_subject_registrations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    filename = (file.filename or "").lower()

    try:
        content = await file.read()

        if filename.endswith(".xlsx"):
            df = pd.read_excel(BytesIO(content), engine="openpyxl")
        elif filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        else:
            raise HTTPException(400, "Upload an XLSX or CSV file.")

        if df.empty:
            raise HTTPException(400, "The uploaded file is empty.")

        columns = {normalize(c): c for c in df.columns}

        register_col = next(
            (columns[x] for x in [
                "registernumber", "registrationnumber",
                "regno", "rollnumber", "studentnumber"
            ] if x in columns),
            None
        )

        subject_col = next(
            (columns[x] for x in [
                "subjectcode", "coursecode",
                "examcode", "papercode"
            ] if x in columns),
            None
        )

        if register_col is None or subject_col is None:
            raise HTTPException(
                400,
                "Required columns: Register Number and Subject Code."
            )

        df = df[[register_col, subject_col]].dropna().copy()
        df.columns = ["register_number", "subject_code"]

        df["register_number"] = df["register_number"].astype(str).str.strip().str.upper()
        df["subject_code"] = df["subject_code"].astype(str).str.strip().str.upper()
        df = df.drop_duplicates()

        students = db.query(Student).filter(
            Student.university_id == university.id,
            Student.is_active.is_(True),
        ).all()

        examinations = db.query(Examination).filter(
            Examination.university_id == university.id
        ).all()

        student_map = {
            s.student_number.strip().upper(): s for s in students
        }

        exam_map = {
            e.exam_code.strip().upper(): e for e in examinations
        }

        errors = []
        grouped = {}

        for row in df.itertuples(index=False):
            register_number = row.register_number
            subject_code = row.subject_code

            student = student_map.get(register_number)
            examination = exam_map.get(subject_code)

            if student is None:
                errors.append(f"Student not found: {register_number}")
                continue

            if examination is None:
                errors.append(f"Subject not found: {subject_code}")
                continue

            grouped.setdefault(examination.id, set()).add(student.id)

        if errors:
            raise HTTPException(
                400,
                detail={
                    "message": "Registration upload contains invalid rows.",
                    "errors": errors[:30],
                    "total_errors": len(errors),
                }
            )

        inserted = 0
        assigned = 0

        for examination_id, student_ids in grouped.items():
            examination = db.query(Examination).filter(
                Examination.id == examination_id,
                Examination.university_id == university.id,
            ).first()

            sessions = db.query(ExamSession).filter(
                ExamSession.examination_id == examination.id,
                ExamSession.university_id == university.id,
            ).order_by(
                ExamSession.exam_date,
                ExamSession.start_time,
                ExamSession.id,
            ).all()

            if not sessions:
                raise HTTPException(
                    400,
                    f"No sessions configured for {examination.exam_code}."
                )

            ordered_students = sorted(
                [student_map_id for student_map_id in student_ids],
                key=lambda sid: student_map[sid].student_number,
            )

            total_capacity = sum(s.capacity for s in sessions)

            if len(ordered_students) > total_capacity:
                raise HTTPException(
                    400,
                    f"{examination.exam_code}: {len(ordered_students)} "
                    f"students but session capacity is {total_capacity}."
                )

            existing = db.query(ExamRegistration).filter(
                ExamRegistration.examination_id == examination.id,
                ExamRegistration.university_id == university.id,
            ).all()

            if existing:
                raise HTTPException(
                    409,
                    f"Registrations already exist for {examination.exam_code}. "
                    "Existing records were preserved."
                )

            position = 0

            for session in sessions:
                batch = ordered_students[
                    position:position + session.capacity
                ]

                for student_id in batch:
                    db.add(
                        ExamRegistration(
                            university_id=university.id,
                            student_id=student_id,
                            examination_id=examination.id,
                            session_id=session.id,
                            registration_status="registered",
                        )
                    )
                    inserted += 1
                    assigned += 1

                position += len(batch)

            examination.student_count = len(ordered_students)

        db.commit()

        return {
            "message": "Registrations uploaded and assigned to sessions.",
            "total_registrations": inserted,
            "total_assigned": assigned,
            "subjects_processed": len(grouped),
            "session_distribution": "Students assigned in student-number order according to session capacity.",
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            500,
            f"Registration upload failed: {str(error)}"
        )
