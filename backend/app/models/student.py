
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from backend.app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    university_id = Column(
        Integer,
        ForeignKey("universities.id"),
        nullable=False,
        index=True,
    )

    student_number = Column(String(30), nullable=False, index=True)

    full_name = Column(String(120), nullable=False)
    department = Column(String(100), nullable=False)
    year_of_study = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "university_id",
            "student_number",
            name="uq_university_student_number",
        ),
    )
