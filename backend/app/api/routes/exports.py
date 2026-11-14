from io import BytesIO
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.app.database import get_db
from backend.app.models import Examination, Allocation, Resource, ExamSession
from backend.app.models.university import University
from backend.app.core.dependencies import get_current_university


router = APIRouter(
    prefix="/api/v1/exports",
    tags=["Excel Exports"]
)


def style_sheet(ws):
    header_fill = PatternFill(
        fill_type="solid",
        fgColor="17365D"
    )

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for column in ws.columns:
        max_length = max(
            len(str(cell.value or ""))
            for cell in column
        )

        ws.column_dimensions[
            get_column_letter(column[0].column)
        ].width = min(max(max_length + 3, 14), 40)


@router.get("/seating-plan")
def download_complete_seating_plan(
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    # Fetch examinations belonging to the logged-in university.
    examinations = (
        db.query(Examination)
        .filter(Examination.university_id == university.id)
        .order_by(
            Examination.exam_date,
            Examination.start_time
        )
        .all()
    )

    if not examinations:
        raise HTTPException(
            status_code=404,
            detail="No examinations found."
        )

    workbook = Workbook()

    # Sheet 1: Complete seating plan
    ws = workbook.active
    ws.title = "Complete Seating Plan"

    ws.append([
        "Exam Code",
        "Subject",
        "Department",
        "Exam Date",
        "Start Time",
        "End Time",
        "Register Number",
        "Student Name",
        "Room Number",
        "Building",
        "Seat Number",
        "Allocation Status"
    ])

    # Sheet 2: Room-wise seating
    room_ws = workbook.create_sheet("Room Wise Seating")

    room_ws.append([
        "Room Number",
        "Building",
        "Exam Code",
        "Subject",
        "Exam Date",
        "Start Time",
        "Seat Number",
        "Register Number",
        "Student Name"
    ])

    # Sheet 3: Examination summary
    exam_ws = workbook.create_sheet("Exam Summary")

    exam_ws.append([
        "Exam Code",
        "Subject",
        "Department",
        "Exam Date",
        "Start Time",
        "End Time",
        "Expected Students",
        "Allocated Students",
        "Rooms Used"
    ])

    # Sheet 4: Room capacity summary
    capacity_ws = workbook.create_sheet("Room Capacity")

    capacity_ws.append([
        "Room Number",
        "Building",
        "Room Capacity",
        "Room Availability",
        "Allocated Seats",
        "Remaining Seats"
    ])

    room_usage = {}

    for examination in examinations:

        # Fetch allocations only for this university.
        allocations = (
            db.query(Allocation)
            .options(
                joinedload(Allocation.student),
                joinedload(Allocation.resource)
            )
            .filter(
                Allocation.university_id == university.id,
                Allocation.examination_id == examination.id
            )
            .order_by(
                Allocation.resource_id,
                Allocation.seat_number
            )
            .all()
        )

        end_time = (
            examination.start_time.hour * 60
            + examination.start_time.minute
            + examination.duration_minutes
        )

        end_hour = (end_time // 60) % 24
        end_minute = end_time % 60

        end_time_text = f"{end_hour:02d}:{end_minute:02d}"

        rooms_used = set()

        for allocation in allocations:
            student = allocation.student
            room = allocation.resource

            rooms_used.add(room.id)

            ws.append([
                examination.exam_code,
                examination.subject_name,
                examination.department,
                examination.exam_date.isoformat(),
                examination.start_time.strftime("%H:%M"),
                end_time_text,
                student.student_number,
                student.full_name,
                room.room_number,
                room.building,
                allocation.seat_number,
                allocation.allocation_status
            ])

            room_ws.append([
                room.room_number,
                room.building,
                examination.exam_code,
                examination.subject_name,
                examination.exam_date.isoformat(),
                examination.start_time.strftime("%H:%M"),
                allocation.seat_number,
                student.student_number,
                student.full_name
            ])

            room_usage[room.id] = (
                room_usage.get(room.id, 0) + 1
            )

        exam_ws.append([
            examination.exam_code,
            examination.subject_name,
            examination.department,
            examination.exam_date.isoformat(),
            examination.start_time.strftime("%H:%M"),
            end_time_text,
            examination.student_count,
            len(allocations),
            len(rooms_used)
        ])

    # Fetch rooms only for the logged-in university.
    resources = (
        db.query(Resource)
        .filter(Resource.university_id == university.id)
        .order_by(Resource.room_number)
        .all()
    )

    for room in resources:
        allocated = room_usage.get(room.id, 0)

        capacity_ws.append([
            room.room_number,
            room.building,
            room.capacity,
            "Available" if room.is_available else "Unavailable",
            allocated,
            max(room.capacity - allocated, 0)
        ])

    # Apply formatting to all worksheets.
    for sheet in workbook.worksheets:
        style_sheet(sheet)

    # Add university information.
    ws.insert_rows(1, 2)
    ws["A1"] = "University"
    ws["B1"] = university.university_name
    ws["A2"] = "University Code"
    ws["B2"] = university.university_code

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    filename = (
        f"{university.university_code}_Seating_Plan.xlsx"
    )

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _style_daily_sheet(ws):
    navy = "17365D"
    blue = "D9EAF7"
    green = "E2F0D9"
    thin_gray = Side(style="thin", color="D9E1F2")

    ws.freeze_panes = "A5"
    ws.sheet_view.showGridLines = False

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="center")
            cell.border = Border(bottom=thin_gray)

    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(color="FFFFFF", bold=True, size=14)
        cell.alignment = Alignment(horizontal="center")

    for row_number in range(2, ws.max_row + 1):
        first_value = ws.cell(row_number, 1).value
        if first_value in ("MORNING SESSION", "AFTERNOON SESSION"):
            fill = green if first_value == "MORNING SESSION" else blue
            ws.merge_cells(
                start_row=row_number,
                start_column=1,
                end_row=row_number,
                end_column=8,
            )
            cell = ws.cell(row_number, 1)
            cell.fill = PatternFill("solid", fgColor=fill)
            cell.font = Font(bold=True, color=navy, size=12)
            cell.alignment = Alignment(horizontal="left")
        elif first_value == "Register Number":
            for cell in ws[row_number]:
                cell.fill = PatternFill("solid", fgColor=navy)
                cell.font = Font(color="FFFFFF", bold=True)
                cell.alignment = Alignment(horizontal="center")

    for column_cells in ws.columns:
        max_length = max(
            (len(str(cell.value or "")) for cell in column_cells),
            default=12,
        )
        ws.column_dimensions[get_column_letter(column_cells[0].column)].width = min(
            max(max_length + 3, 14), 36
        )

    ws.auto_filter.ref = f"A1:H{ws.max_row}"


@router.get("/daily-seating-plan/{exam_date}")
def download_daily_seating_plan(
    exam_date: date,
    db: Session = Depends(get_db),
    university: University = Depends(get_current_university),
):
    """Export one examination day as one workbook with morning/afternoon sections.

    The workbook is generated from current database allocations at download time.
    It does not update or overwrite previously downloaded files.
    """
    sessions = (
        db.query(ExamSession)
        .filter(
            ExamSession.university_id == university.id,
            ExamSession.exam_date == exam_date,
        )
        .order_by(ExamSession.start_time, ExamSession.id)
        .all()
    )

    if not sessions:
        raise HTTPException(status_code=404, detail="No examination sessions found for this date.")

    session_data = []
    subject_codes = set()

    for session in sessions:
        examination = (
            db.query(Examination)
            .filter(
                Examination.id == session.examination_id,
                Examination.university_id == university.id,
            )
            .first()
        )
        if examination is None:
            continue

        subject_codes.add(examination.exam_code or f"EXAM{examination.id}")

        allocations = (
            db.query(Allocation)
            .options(
                joinedload(Allocation.student),
                joinedload(Allocation.resource),
            )
            .filter(
                Allocation.university_id == university.id,
                Allocation.session_id == session.id,
                Allocation.examination_id == examination.id,
            )
            .order_by(Allocation.resource_id, Allocation.seat_number)
            .all()
        )

        period = "MORNING SESSION" if session.start_time.hour < 12 else "AFTERNOON SESSION"
        session_data.append((period, session, examination, allocations))

    if not session_data:
        raise HTTPException(status_code=404, detail="No valid examination sessions found for this date.")

    workbook = Workbook()
    ws = workbook.active
    ws.title = "Daily Seating Plan"

    ws.append([f"{university.university_name} - DAILY EXAMINATION SEATING PLAN"])
    ws.append(["University Code", university.university_code, "Examination Date", exam_date.isoformat()])
    ws.append(["Subjects", ", ".join(sorted(subject_codes)), "Total Sessions", len(session_data)])
    ws.append([])

    for period_name in ("MORNING SESSION", "AFTERNOON SESSION"):
        matching = [item for item in session_data if item[0] == period_name]
        ws.append([period_name])

        if not matching:
            ws.append(["No session scheduled for this period."])
            ws.append([])
            continue

        for _, session, examination, allocations in matching:
            ws.append([
                "Subject", examination.exam_code,
                "Subject Name", examination.subject_name,
                "Session ID", session.id,
                "Start Time", session.start_time.strftime("%H:%M"),
            ])
            ws.append([
                "Register Number", "Student Name", "Department", "Year",
                "Block", "Room Number", "Seat Number", "Allocation Status",
            ])

            for allocation in allocations:
                student = allocation.student
                room = allocation.resource
                ws.append([
                    student.student_number if student else "",
                    student.full_name if student else "",
                    student.department if student else "",
                    getattr(student, "year_of_study", "") if student else "",
                    room.building if room else "",
                    room.room_number if room else "",
                    allocation.seat_number,
                    allocation.allocation_status,
                ])

            ws.append(["Total Allocated", len(allocations)])
            ws.append([])

    _style_daily_sheet(ws)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    subject_part = "_".join(sorted(subject_codes))[:60].replace("/", "-")
    filename = f"{university.university_code}_{exam_date.isoformat()}_{subject_part}_Seating_Plan.xlsx"

    return StreamingResponse(
        output,
        media_type=EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
