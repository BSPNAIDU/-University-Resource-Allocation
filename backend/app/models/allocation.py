from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False, index=True)

    seat_number = Column(String(20), nullable=False)
    allocation_status = Column(String(30), default="allocated", nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    student = relationship("Student")
    examination = relationship("Examination")
    session = relationship("ExamSession")
    resource = relationship("Resource")

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "resource_id",
            "seat_number",
            name="uq_session_room_seat"
        ),
        UniqueConstraint(
            "student_id",
            "examination_id",
            name="uq_student_examination"
        ),
    )
