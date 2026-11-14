from sqlalchemy import Column, Integer, Boolean, Date, ForeignKey, UniqueConstraint
from backend.app.database import Base


class ResourceDateAvailability(Base):
    __tablename__ = "resource_date_availability"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"), nullable=False, index=True)
    resource_id = Column(Integer, ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, index=True)
    is_available = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "university_id", "resource_id", "exam_date",
            name="uq_resource_date_availability"
        ),
    )
