from io import BytesIO

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.student import Student
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university


router = APIRouter(
    prefix="/api/v1/students",
    tags=["Students"]
)


class StudentCreate(BaseModel):
    student_number: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=100)
    year_of_study: int = Field(ge=1, le=8)


class StudentResponse(BaseModel):
    id: int
    student_number: str
    full_name: str
    department: str
    year_of_study: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.post(
    "/",
    response_model=StudentResponse,
    status_code=status.HTTP_201_CREATED
)
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    existing = db.query(Student).filter(
        Student.university_id == university.id,
        Student.student_number == student_data.student_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this student number already exists."
        )

    student = Student(
        university_id=university.id,
        **student_data.model_dump()
    )

    db.add(student)
    db.commit()
    db.refresh(student)

    return student


@router.post("/upload")
async def upload_students(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    filename = (file.filename or "").lower()

    try:
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        if filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(contents), dtype=str)
        elif filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(contents), dtype=str)
        else:
            raise HTTPException(
                status_code=400,
                detail="Only Excel (.xlsx, .xls) and CSV files are supported."
            )

        if df.empty:
            raise HTTPException(status_code=400, detail="No student rows found.")

        # Automatically recognize fixed column names and common equivalents.
        aliases = {
            "register number": "student_number",
            "register_number": "student_number",
            "registration number": "student_number",
            "student number": "student_number",
            "student_number": "student_number",
            "student name": "full_name",
            "student_name": "full_name",
            "full name": "full_name",
            "full_name": "full_name",
            "department": "department",
            "branch": "department",
            "year": "year_of_study",
            "year of study": "year_of_study",
            "year_of_study": "year_of_study"
        }

        column_map = {}
        for column in df.columns:
            normalized = str(column).strip().lower()
            if normalized in aliases:
                column_map[aliases[normalized]] = column

        required = ["student_number", "full_name", "department", "year_of_study"]
        missing = [field for field in required if field not in column_map]

        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing required columns. Use: Register Number, "
                    "Student Name, Department, Year."
                )
            )

        df = df.fillna("")
        existing_numbers = set(
            value[0] for value in db.query(Student.student_number).filter(
                Student.university_id == university.id
            ).all()
        )

        seen_numbers = set()
        records = []
        duplicate_count = 0
        invalid_count = 0
        errors = []

        for index, row in df.iterrows():
            excel_row = index + 2

            student_number = str(row[column_map["student_number"]]).strip()
            full_name = str(row[column_map["full_name"]]).strip()
            department = str(row[column_map["department"]]).strip()
            year_value = str(row[column_map["year_of_study"]]).strip()

            if not all([student_number, full_name, department, year_value]):
                invalid_count += 1
                if len(errors) < 20:
                    errors.append(f"Row {excel_row}: One or more fields are empty.")
                continue

            if len(student_number) > 30 or len(full_name) > 120 or len(department) > 100:
                invalid_count += 1
                if len(errors) < 20:
                    errors.append(f"Row {excel_row}: A field exceeds its maximum length.")
                continue

            try:
                year_text = str(year_value).strip().lower()

                year_words = {
                    "first year": 1, "first": 1,
                    "second year": 2, "second": 2,
                    "third year": 3, "third": 3,
                    "fourth year": 4, "fourth": 4
                }

                if year_text in year_words:
                    year = year_words[year_text]
                else:
                    year_text = year_text.replace(" year", "").strip()

                    for suffix in ["st", "nd", "rd", "th"]:
                        if year_text.endswith(suffix):
                            year_text = year_text[:-2]
                            break

                    year = int(float(year_text))
            except (ValueError, TypeError):
                invalid_count += 1
                if len(errors) < 20:
                    errors.append(f"Row {excel_row}: Year must be a number.")
                continue

            if year < 1 or year > 8:
                invalid_count += 1
                if len(errors) < 20:
                    errors.append(f"Row {excel_row}: Year must be between 1 and 8.")
                continue

            if student_number in existing_numbers or student_number in seen_numbers:
                duplicate_count += 1
                continue

            seen_numbers.add(student_number)

            records.append({
                "university_id": university.id,
                "student_number": student_number,
                "full_name": full_name,
                "department": department,
                "year_of_study": year,
                "is_active": True
            })

        if records:
            db.bulk_insert_mappings(Student, records)
            db.commit()

        return {
            "message": "Student upload processed successfully.",
            "total_rows": len(df),
            "inserted": len(records),
            "duplicates_skipped": duplicate_count,
            "invalid_rows": invalid_count,
            "errors": errors
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Student upload failed: {str(exc)}"
        )


@router.get("/", response_model=list[StudentResponse])
def list_students(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    return (
        db.query(Student)
        .filter(Student.university_id == university.id)
        .order_by(Student.id)
        .all()
    )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university)
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.university_id == university.id
    ).first()

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found."
        )

    return student
