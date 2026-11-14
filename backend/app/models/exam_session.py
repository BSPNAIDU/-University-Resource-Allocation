from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey, UniqueConstraint
from backend.app.database import Base

class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id"), nullable=False, index=True)
    session_name = Column(String(50), nullable=False)
    exam_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False, default=300)

    __table_args__ = (
        UniqueConstraint("examination_id", "session_name", name="uq_examination_session_name"),
    )
