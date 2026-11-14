from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.app.database import Base


class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)

    university_name = Column(
        String(200),
        nullable=False,
        unique=True,
        index=True
    )

    university_code = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True
    )

    password_hash = Column(String(255), nullable=True)

    address = Column(String(300), nullable=True)

    city = Column(String(100), nullable=True)

    state = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )
