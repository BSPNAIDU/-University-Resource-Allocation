from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.app.database import Base

class ExamRegistration(Base):
    __tablename__ = "exam_registrations"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False, index=True)
    registration_status = Column(String(30), default="registered", nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    student = relationship("Student")
    examination = relationship("Examination")
    session = relationship("ExamSession")

    __table_args__ = (
        UniqueConstraint("student_id", "examination_id", name="uq_student_exam_registration"),
    )
