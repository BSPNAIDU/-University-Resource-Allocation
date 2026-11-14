from backend.app.models.university import University
from backend.app.models.student import Student
from backend.app.models.resource import Resource
from backend.app.models.examination import Examination
from backend.app.models.exam_session import ExamSession
from backend.app.models.registration import ExamRegistration
from backend.app.models.allocation import Allocation
from backend.app.models.resource_date_availability import ResourceDateAvailability

__all__ = [
    "University",
    "Student",
    "Resource",
    "Examination",
    "ExamSession",
    "ExamRegistration",
    "Allocation",
    "ResourceDateAvailability",
]
