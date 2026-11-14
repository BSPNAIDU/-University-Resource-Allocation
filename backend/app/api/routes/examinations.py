from io import BytesIO
import re

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.dependencies import get_current_university
from backend.app.models import (
    Examination, ExamSession, Student, ExamRegistration, Resource
)
from backend.app.models.university import University

router = APIRouter(prefix="/api/v1/examinations", tags=["Examinations"])


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def find_column(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None


def parse_schedule_groups(notes_df):
    """
    Read register-number ranges from the optional Schedule Notes sheet.
    Expected examples:
      Group 1 | BSP26CSE0001 to BSP26CSE0300; morning sessions
      Group 2 | BSP26CSE0301 to BSP26CSE0500; afternoon sessions
    """
    if notes_df is None or notes_df.empty or len(notes_df.columns) < 2:
        return []

    key_col = notes_df.columns[0]
    value_col = notes_df.columns[1]
    groups = []

    for _, row in notes_df.iterrows():
        label = str(row[key_col]).strip()
        details = str(row[value_col]).strip()

        if not re.match(r"group\s*\d+", label, flags=re.IGNORECASE):
            continue

        matches = re.findall(
            r"([A-Za-z0-9_-]+)\s+to\s+([A-Za-z0-9_-]+)",
            details,
            flags=re.IGNORECASE
        )
        if not matches:
            continue

        start_number, end_number = matches[0]
        lowered = details.lower()

        if "morning" in lowered or "forenoon" in lowered:
            period = "morning"
        elif "afternoon" in lowered or "evening" in lowered:
            period = "afternoon"
        else:
            period = None

        groups.append({
            "label": label,
            "start": start_number.strip().upper(),
            "end": end_number.strip().upper(),
            "period": period,
        })

    return groups


def session_period(start_time):
    return "morning" if start_time.hour < 12 else "afternoon"


def auto_create_registrations(db, university, groups):
    """
    Create student -> subject -> session links from the already-uploaded
    student master and timetable Schedule Notes. No third registration file.
    Existing matching registrations are retained; conflicting mappings fail
    safely rather than silently moving students.
    """
    if not groups:
        return {
            "created_registrations": 0,
            "already_registered": 0,
            "subjects_registered": 0,
            "registration_message": (
                "No Group register ranges were found in the Schedule Notes sheet. "
                "No registrations were generated."
            ),
        }

    students = db.query(Student).filter(
        Student.university_id == university.id,
        Student.is_active.is_(True),
    ).all()

    if not students:
        raise HTTPException(
            400,
            "Upload student details before importing the examination timetable."
        )

    student_map = {s.student_number.strip().upper(): s for s in students}
    sorted_numbers = sorted(student_map)

    group_students = {}
    for group in groups:
        start = group["start"]
        end = group["end"]
        selected = [
            student_map[number]
            for number in sorted_numbers
            if start <= number <= end
        ]
        if not selected:
            raise HTTPException(
                400,
                f"{group['label']} range {start} to {end} matched no uploaded students."
            )

        # Check that every number in the stated range is present. Register
        # numbers are treated as identifiers, not converted to integers.
        if start not in student_map or end not in student_map:
            raise HTTPException(
                400,
                f"{group['label']} boundaries do not both exist in uploaded student records."
            )

        group_students[group["period"]] = selected

    if None in group_students or "morning" not in group_students or "afternoon" not in group_students:
        raise HTTPException(
            400,
            "Schedule Notes must define both morning and afternoon register-number groups."
        )

    rooms = db.query(Resource).filter(
        Resource.university_id == university.id,
        Resource.is_available.is_(True),
    ).all()
    total_room_capacity = sum(int(room.capacity) for room in rooms)

    examinations = db.query(Examination).filter(
        Examination.university_id == university.id
    ).all()

    created = 0
    already_registered = 0
    processed_subjects = 0

    for examination in examinations:
        sessions = db.query(ExamSession).filter(
            ExamSession.university_id == university.id,
            ExamSession.examination_id == examination.id,
        ).order_by(
            ExamSession.exam_date,
            ExamSession.start_time,
            ExamSession.id,
        ).all()

        if not sessions:
            continue

        sessions_by_period = {}
        for session in sessions:
            period = session_period(session.start_time)
            if period in sessions_by_period:
                raise HTTPException(
                    400,
                    f"{examination.exam_code}: more than one {period} session exists "
                    "for this subject. The timetable must identify one session per group."
                )
            sessions_by_period[period] = session

        for period in ("morning", "afternoon"):
            if period not in sessions_by_period:
                raise HTTPException(
                    400,
                    f"{examination.exam_code}: missing {period} session required by Schedule Notes."
                )

        existing = db.query(ExamRegistration).filter(
            ExamRegistration.university_id == university.id,
            ExamRegistration.examination_id == examination.id,
        ).all()
        existing_by_student = {item.student_id: item for item in existing}

        subject_created = 0
        expected_total = 0

        for period in ("morning", "afternoon"):
            session = sessions_by_period[period]
            selected_students = group_students[period]
            expected_total += len(selected_students)

            # Keep the session limit aligned with all currently available rooms.
            if total_room_capacity > 0:
                session.capacity = total_room_capacity

            for student in selected_students:
                current = existing_by_student.get(student.id)

                if current is not None:
                    if current.session_id != session.id:
                        raise HTTPException(
                            409,
                            f"{student.student_number} is already registered for "
                            f"{examination.exam_code} in a different session. "
                            "Existing registration was not changed."
                        )
                    already_registered += 1
                    continue

                db.add(ExamRegistration(
                    university_id=university.id,
                    student_id=student.id,
                    examination_id=examination.id,
                    session_id=session.id,
                    registration_status="registered",
                ))
                created += 1
                subject_created += 1

        examination.student_count = expected_total
        processed_subjects += 1

    return {
        "created_registrations": created,
        "already_registered": already_registered,
        "subjects_registered": processed_subjects,
        "registration_message": (
            "Student registrations were generated automatically from the "
            "student master and timetable Schedule Notes."
        ),
    }


@router.post("/upload")
@router.post("/upload-timetable")
async def upload_timetable(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    filename = (file.filename or "").lower()

    try:
        content = await file.read()

        notes_df = None
        if filename.endswith(".xlsx"):
            workbook = pd.read_excel(
                BytesIO(content),
                sheet_name=None,
                engine="openpyxl"
            )
            if not workbook:
                raise HTTPException(400, "The timetable workbook is empty.")

            # The first sheet is the timetable; Schedule Notes is optional.
            timetable_sheet = next(
                (name for name in workbook if normalize(name) in {
                    "examinationtimetable", "timetable", "examschedule"
                }),
                next(iter(workbook))
            )
            df = workbook[timetable_sheet]

            notes_sheet = next(
                (name for name in workbook if normalize(name) in {
                    "schedulenotes", "notes", "allocationnotes"
                }),
                None
            )
            if notes_sheet is not None:
                notes_df = workbook[notes_sheet]

        elif filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        else:
            raise HTTPException(400, "Upload an XLSX or CSV timetable.")

        if df.empty:
            raise HTTPException(400, "The timetable file is empty.")

        columns = {normalize(c): c for c in df.columns}

        code_col = find_column(columns, [
            "subjectcode", "coursecode", "examcode", "papercode",
            "subjectid", "courseid"
        ])
        name_col = find_column(columns, [
            "subjectname", "coursename", "examname", "subject",
            "papername", "course"
        ])
        department_col = find_column(columns, [
            "department", "branch", "program", "stream"
        ])
        date_col = find_column(columns, [
            "examdate", "date", "examinationdate"
        ])
        start_col = find_column(columns, [
            "starttime", "fromtime", "examstarttime", "time"
        ])
        end_col = find_column(columns, [
            "endtime", "totime", "examendtime"
        ])
        duration_col = find_column(columns, [
            "duration", "durationminutes", "examduration"
        ])

        missing = []
        if name_col is None:
            missing.append("Subject Name")
        if date_col is None:
            missing.append("Exam Date")
        if start_col is None:
            missing.append("Start Time")

        if missing:
            raise HTTPException(
                400,
                "Missing required timetable columns: " + ", ".join(missing)
            )

        created_examinations = 0
        created_sessions = 0
        skipped_sessions = 0
        errors = []

        for row_number, row in df.iterrows():
            try:
                subject_name = str(row[name_col]).strip()
                if not subject_name or subject_name.lower() == "nan":
                    raise ValueError("Subject name is empty.")

                exam_code = None
                if code_col is not None and pd.notna(row[code_col]):
                    value = str(row[code_col]).strip()
                    if value and value.lower() != "nan":
                        exam_code = value.upper()

                department = "General"
                if department_col is not None and pd.notna(row[department_col]):
                    value = str(row[department_col]).strip()
                    if value and value.lower() != "nan":
                        department = value

                exam_date = pd.to_datetime(row[date_col], errors="raise").date()
                start_value = pd.to_datetime(str(row[start_col]), errors="raise")
                start_time = start_value.time()

                if end_col is not None and pd.notna(row[end_col]):
                    end_value = pd.to_datetime(str(row[end_col]), errors="raise")
                    end_time = end_value.time()
                    start_minutes = start_time.hour * 60 + start_time.minute
                    end_minutes = end_time.hour * 60 + end_time.minute
                    duration = end_minutes - start_minutes
                    if duration <= 0:
                        raise ValueError("End time must be after start time.")
                elif duration_col is not None and pd.notna(row[duration_col]):
                    duration_value = str(row[duration_col]).strip().lower()
                    match = re.search(r"\d+", duration_value)
                    if not match:
                        raise ValueError("Invalid duration.")
                    duration = int(match.group())
                else:
                    raise ValueError(
                        "Provide End Time or Duration for every timetable row."
                    )

                if exam_code:
                    examination = db.query(Examination).filter(
                        Examination.university_id == university.id,
                        Examination.exam_code == exam_code
                    ).first()
                else:
                    examination = db.query(Examination).filter(
                        Examination.university_id == university.id,
                        Examination.exam_code.is_(None),
                        Examination.subject_name.ilike(subject_name),
                        Examination.department.ilike(department)
                    ).first()

                if examination is not None:
                    if examination.subject_name.strip().casefold() != subject_name.casefold():
                        raise ValueError(
                            f"Subject code {exam_code} is already linked to "
                            f"{examination.subject_name}, not {subject_name}."
                        )
                else:
                    examination = Examination(
                        university_id=university.id,
                        exam_code=exam_code,
                        subject_name=subject_name,
                        department=department,
                        exam_date=exam_date,
                        start_time=start_time,
                        duration_minutes=duration,
                        student_count=0
                    )
                    db.add(examination)
                    db.flush()
                    created_examinations += 1

                session_name = (
                    exam_date.strftime("%Y%m%d") + "-" +
                    start_time.strftime("%H%M")
                )

                existing_session = db.query(ExamSession).filter(
                    ExamSession.university_id == university.id,
                    ExamSession.examination_id == examination.id,
                    ExamSession.session_name == session_name
                ).first()

                if existing_session:
                    skipped_sessions += 1
                    continue

                session = ExamSession(
                    university_id=university.id,
                    examination_id=examination.id,
                    session_name=session_name,
                    exam_date=exam_date,
                    start_time=start_time,
                    duration_minutes=duration,
                    capacity=300
                )
                db.add(session)
                created_sessions += 1

            except Exception as row_error:
                errors.append(f"Excel row {row_number + 2}: {str(row_error)}")

        if errors:
            db.rollback()
            raise HTTPException(
                400,
                detail={
                    "message": "Timetable upload was cancelled because some rows are invalid.",
                    "errors": errors[:30],
                    "total_errors": len(errors)
                }
            )

        db.flush()

        groups = parse_schedule_groups(notes_df)
        registration_result = auto_create_registrations(
            db=db,
            university=university,
            groups=groups
        )

        db.commit()

        return {
            "message": "Timetable imported and automatic registration processing completed.",
            "new_subjects": created_examinations,
            "new_sessions": created_sessions,
            "duplicate_sessions_skipped": skipped_sessions,
            **registration_result,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(500, f"Timetable upload failed: {str(error)}")


@router.get("/")
def get_examinations(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    return db.query(Examination).filter(
        Examination.university_id == university.id
    ).order_by(Examination.id.desc()).all()


@router.get("/sessions")
def get_exam_sessions(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    return db.query(ExamSession).filter(
        ExamSession.university_id == university.id
    ).order_by(
        ExamSession.exam_date,
        ExamSession.start_time
    ).all()


@router.get("/{examination_id}")
def get_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    examination = db.query(Examination).filter(
        Examination.id == examination_id,
        Examination.university_id == university.id
    ).first()

    if examination is None:
        raise HTTPException(404, "Examination not found.")

    return examination
