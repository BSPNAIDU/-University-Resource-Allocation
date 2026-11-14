
from backend.app.database import SessionLocal
from backend.app.models.student import Student
from backend.app.models.examination import Examination
from backend.app.models.registration import ExamRegistration
from backend.app.models.allocation import Allocation
from backend.app.models.resource import Resource

db = SessionLocal()

try:
    print("\nBEFORE CLEANUP")
    print("-------------------------")
    print("Allocations:", db.query(Allocation).count())
    print("Registrations:", db.query(ExamRegistration).count())
    print("Examinations:", db.query(Examination).count())
    print("Students:", db.query(Student).count())
    print("Rooms:", db.query(Resource).count())

    confirmation = input(
        "\nDelete all old student and examination data? "
        "All rooms will be preserved. Type YES to continue: "
    )

    if confirmation != "YES":
        print("Cleanup cancelled.")
    else:
        db.query(Allocation).delete(synchronize_session=False)
        db.query(ExamRegistration).delete(synchronize_session=False)
        db.query(Examination).delete(synchronize_session=False)
        db.query(Student).delete(synchronize_session=False)

        db.query(Resource).update(
            {Resource.is_available: True},
            synchronize_session=False
        )

        db.commit()

        print("\nCLEANUP COMPLETED")
        print("-------------------------")
        print("Allocations:", db.query(Allocation).count())
        print("Registrations:", db.query(ExamRegistration).count())
        print("Examinations:", db.query(Examination).count())
        print("Students:", db.query(Student).count())
        print("Rooms preserved:", db.query(Resource).count())
        print(
            "Available rooms:",
            db.query(Resource).filter(
                Resource.is_available == True
            ).count()
        )

except Exception as error:
    db.rollback()
    print("\nCLEANUP FAILED:", error)

finally:
    db.close()
