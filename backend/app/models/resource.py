
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from backend.app.database import Base


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)

    university_id = Column(
        Integer,
        ForeignKey("universities.id"),
        nullable=False,
        index=True
    )

    room_number = Column(String(30), nullable=False, index=True)
    building = Column(String(100), nullable=False)
    capacity = Column(Integer, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    room_type = Column(
        String(50),
        default="Examination Hall",
        nullable=False
    )
