
from datetime import datetime, timedelta
from io import BytesIO
import json
import re

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Student, Examination, ExamRegistration
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university

router = APIRouter(
    prefix="/api/v1/uploads",
    tags=["File Upload"],
)

REQUIRED_COLUMNS = [
    "register_number",
    "student_name",
    "department",
    "year",
    "subject_code",
    "subject_name",
    "exam_date",
    "start_time",
    "end_time",
]


COLUMN_ALIASES = {
    "register_number": [
        "register_number", "register no", "register number",
        "registration number", "registration no", "reg no",
        "reg_number", "roll no", "roll number", "roll_no",
        "student id", "student_id", "enrollment no",
        "enrollment number", "admission number"
    ],
    "student_name": [
        "student_name", "student name", "name",
        "full name", "candidate name", "learner name"
    ],
    "department": [
        "department", "dept", "branch", "course",
        "department name", "program", "programme"
    ],
    "year": [
        "year", "year of study", "study year",
        "academic year", "current year", "semester year"
    ],
    "subject_code": [
        "subject_code", "subject code", "course code",
        "paper code", "exam code", "course_id"
    ],
    "subject_name": [
        "subject_name", "subject name", "course name",
        "paper name", "exam name", "title"
    ],
    "exam_date": [
        "exam_date", "exam date", "date",
        "examination date", "test date"
    ],
    "start_time": [
        "start_time", "start time", "from time",
        "exam start", "time from"
    ],
    "end_time": [
        "end_time", "end time", "to time",
        "exam end", "time to"
    ],
}


def normalize_column_name(value):
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def suggest_column_mapping(columns):
    normalized = {
        normalize_column_name(column): column
        for column in columns
    }

    mapping = {}

    for standard_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_column_name(alias)

            if key in normalized:
                mapping[standard_name] = normalized[key]
                break

    return mapping


def apply_column_mapping(df, manual_mapping=None):
    suggested = suggest_column_mapping(df.columns)
    mapping = dict(suggested)

    if manual_mapping:
        try:
            supplied = (
                json.loads(manual_mapping)
                if isinstance(manual_mapping, str)
                else manual_mapping
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Column mapping must be valid JSON."
            )

        if not isinstance(supplied, dict):
            raise HTTPException(
                status_code=400,
                detail="Column mapping must be a JSON object."
            )

        for standard_name, source_column in supplied.items():
            if standard_name not in REQUIRED_COLUMNS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown target column: {standard_name}"
                )

            if source_column in df.columns:
                mapping[standard_name] = source_column

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in mapping
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some required columns could not be recognised.",
                "missing_columns": missing,
                "available_columns": [str(c) for c in df.columns],
                "suggested_mapping": mapping,
                "instruction": "Select the matching source columns and submit them as a JSON mapping."
            }
        )

    selected = {}

    for standard_name in REQUIRED_COLUMNS:
        selected[standard_name] = mapping[standard_name]

    df = df.rename(
        columns={
            source: target
            for target, source in selected.items()
        }
    )

    return df[REQUIRED_COLUMNS].copy(), mapping


def read_uploaded_dataframe(filename, file_content):
    filename = (filename or "").lower()

    if filename.endswith(".csv"):
        return pd.read_csv(BytesIO(file_content))

    if filename.endswith(".xlsx"):
        return pd.read_excel(BytesIO(file_content), engine="openpyxl")

    raise HTTPException(
        status_code=400,
        detail="Only CSV and XLSX files are supported."
    )


@router.post("/preview")
async def preview_students_examinations(
    file: UploadFile = File(...),
    university: University = Depends(get_current_university),
):
    try:
        file_content = await file.read()
        df = read_uploaded_dataframe(file.filename, file_content)

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file contains no records."
            )

        mapping = suggest_column_mapping(df.columns)

        return {
            "message": "File preview generated.",
            "university": university.university_name,
            "filename": file.filename,
            "total_rows": len(df),
            "available_columns": [str(c) for c in df.columns],
            "suggested_mapping": mapping,
            "unrecognised_fields": [
                field for field in REQUIRED_COLUMNS
                if field not in mapping
            ],
            "preview_rows": (
                df.head(10)
                .fillna("")
                .astype(str)
                .to_dict(orient="records")
            )
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to preview file: {str(error)}"
        )


@router.post("/students-examinations")
async def upload_students_examinations(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
    mapping: str = Form(None),
):
    try:
        file_content = await file.read()
        df = read_uploaded_dataframe(file.filename, file_content)
        df, detected_mapping = apply_column_mapping(df, mapping)

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read uploaded file: {str(error)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file contains no student records.",
        )

    if df.isnull().any().any():
        missing_rows = (
            df[df.isnull().any(axis=1)].index + 2
        ).tolist()

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Some rows contain missing values.",
                "csv_row_numbers": missing_rows,
            },
        )

    for column in [
        "register_number",
        "student_name",
        "department",
        "subject_code",
        "subject_name",
    ]:
        df[column] = df[column].astype(str).str.strip()

    if (
        df[REQUIRED_COLUMNS]
        .astype(str)
        .apply(lambda column: column.str.strip().eq(""))
    ).any().any():
        raise HTTPException(
            status_code=400,
            detail="Empty values are not allowed.",
        )

    if df["register_number"].duplicated().any():
        duplicates = (
            df.loc[
                df["register_number"].duplicated(keep=False),
                "register_number"
            ].unique().tolist()
        )

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Duplicate registration numbers found in the file.",
                "duplicates": duplicates,
            },
        )

    try:
        df["year"] = pd.to_numeric(df["year"], errors="raise")

        if (
            (df["year"] < 1).any()
            or (df["year"] > 10).any()
            or (df["year"] % 1 != 0).any()
        ):
            raise ValueError(
                "Year of study must be a whole number from 1 to 10."
            )

        df["exam_date"] = pd.to_datetime(
            df["exam_date"],
            errors="raise"
        ).dt.date

        df["start_time"] = pd.to_datetime(
            df["start_time"].astype(str),
            errors="raise"
        ).dt.time

        df["end_time"] = pd.to_datetime(
            df["end_time"].astype(str),
            errors="raise"
        ).dt.time

        for _, row in df.iterrows():
            if row["end_time"] <= row["start_time"]:
                raise ValueError(
                    f"End time must be after start time for "
                    f"{row['subject_code']}."
                )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date, time, or year value: {str(error)}",
        )

    exam_groups = df.groupby(
        ["subject_code", "exam_date"],
        dropna=False,
    )

    for (subject_code, exam_date), group in exam_groups:
        schedules = group[
            ["department", "subject_name", "start_time", "end_time"]
        ].drop_duplicates()

        if len(schedules) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Inconsistent examination details for "
                    f"{subject_code} on {exam_date}."
                ),
            )

    try:
        students_added = 0
        examinations_added = 0
        registrations_added = 0

        for _, row in df.iterrows():

            # Find student only within the logged-in university.
            student = (
                db.query(Student)
                .filter(
                    Student.university_id == university.id,
                    Student.student_number == row["register_number"],
                )
                .first()
            )

            if student is None:
                student = Student(
                    university_id=university.id,
                    student_number=row["register_number"],
                    full_name=row["student_name"],
                    department=row["department"],
                    year_of_study=int(row["year"]),
                    is_active=True,
                )

                db.add(student)
                db.flush()
                students_added += 1

            else:
                if (
                    student.full_name != row["student_name"]
                    or student.department != row["department"]
                    or student.year_of_study != int(row["year"])
                ):
                    raise ValueError(
                        f"Student details do not match existing record: "
                        f"{row['register_number']}."
                    )

            exam_code = (
                f"{row['subject_code']}-"
                f"{row['exam_date'].strftime('%Y%m%d')}"
            )

            # Find examination only within the logged-in university.
            examination = (
                db.query(Examination)
                .filter(
                    Examination.university_id == university.id,
                    Examination.exam_code == exam_code,
                )
                .first()
            )

            start_datetime = datetime.combine(
                row["exam_date"], row["start_time"]
            )

            end_datetime = datetime.combine(
                row["exam_date"], row["end_time"]
            )

            duration = int(
                (end_datetime - start_datetime).total_seconds() / 60
            )

            if examination is None:
                examination = Examination(
                    university_id=university.id,
                    exam_code=exam_code,
                    subject_name=row["subject_name"],
                    department=row["department"],
                    exam_date=row["exam_date"],
                    start_time=row["start_time"],
                    duration_minutes=duration,
                    student_count=0,
                )

                db.add(examination)
                db.flush()
                examinations_added += 1

            else:
                if (
                    examination.subject_name != row["subject_name"]
                    or examination.department != row["department"]
                    or examination.start_time != row["start_time"]
                    or examination.duration_minutes != duration
                ):
                    raise ValueError(
                        f"Examination details conflict with existing record: "
                        f"{exam_code}."
                    )

            # Find registration within this university.
            registration = (
                db.query(ExamRegistration)
                .filter(
                    ExamRegistration.university_id == university.id,
                    ExamRegistration.student_id == student.id,
                    ExamRegistration.examination_id == examination.id,
                )
                .first()
            )

            if registration is None:

                # Check overlapping exams for this student's schedule.
                existing_registrations = (
                    db.query(ExamRegistration, Examination)
                    .join(
                        Examination,
                        ExamRegistration.examination_id == Examination.id,
                    )
                    .filter(
                        ExamRegistration.university_id == university.id,
                        Examination.university_id == university.id,
                        ExamRegistration.student_id == student.id,
                        ExamRegistration.registration_status == "registered",
                        Examination.id != examination.id,
                        Examination.exam_date == examination.exam_date,
                    )
                    .all()
                )

                current_start = datetime.combine(
                    examination.exam_date,
                    examination.start_time,
                )

                current_end = current_start + timedelta(
                    minutes=examination.duration_minutes
                )

                for existing_registration, existing_exam in existing_registrations:

                    existing_start = datetime.combine(
                        existing_exam.exam_date,
                        existing_exam.start_time,
                    )

                    existing_end = existing_start + timedelta(
                        minutes=existing_exam.duration_minutes
                    )

                    if (
                        current_start < existing_end
                        and existing_start < current_end
                    ):
                        raise ValueError(
                            f"Schedule conflict for student "
                            f"{student.student_number}: already registered "
                            f"for {existing_exam.exam_code}, which overlaps "
                            f"with {examination.exam_code}."
                        )

                registration = ExamRegistration(
                    university_id=university.id,
                    student_id=student.id,
                    examination_id=examination.id,
                    registration_status="registered",
                )

                db.add(registration)
                db.flush()
                registrations_added += 1

        # Update student counts only for this university's examinations.
        uploaded_exam_codes = [
            f"{subject_code}-{exam_date.strftime('%Y%m%d')}"
            for subject_code, exam_date in exam_groups.groups.keys()
        ]

        examinations = (
            db.query(Examination)
            .filter(
                Examination.university_id == university.id,
                Examination.exam_code.in_(uploaded_exam_codes),
            )
            .all()
        )

        for examination in examinations:
            examination.student_count = (
                db.query(ExamRegistration)
                .filter(
                    ExamRegistration.university_id == university.id,
                    ExamRegistration.examination_id == examination.id,
                    ExamRegistration.registration_status == "registered",
                )
                .count()
            )

        db.commit()

        return {
            "message": "File uploaded and processed successfully.",
            "university": university.university_name,
            "filename": file.filename,
            "total_rows": len(df),
            "new_students": students_added,
            "new_examinations": examinations_added,
            "new_registrations": registrations_added,
            "note": "Existing matching student and registration records were preserved.",
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=f"Upload was rolled back: {str(error)}",
        )
