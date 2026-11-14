from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, UniqueConstraint
from backend.app.database import Base

class Examination(Base):
    __tablename__ = "examinations"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    exam_code = Column(String(30), nullable=True, index=True)
    subject_name = Column(String(150), nullable=False)
    department = Column(String(100), nullable=False)
    exam_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    student_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("university_id", "exam_code", name="uq_university_exam_code"),
    )
