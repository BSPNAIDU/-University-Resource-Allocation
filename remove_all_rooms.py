
from backend.app.database import SessionLocal
from backend.app.models.resource import Resource
from backend.app.models.allocation import Allocation

db = SessionLocal()

try:
    room_count = db.query(Resource).count()
    allocation_count = db.query(Allocation).count()

    print("ROOM CLEANUP")
    print("-------------------------")
    print("Existing rooms:", room_count)
    print("Existing allocations:", allocation_count)

    confirmation = input(
        "\nDelete ALL rooms and their seating allocations? "
        "Type DELETE ROOMS to continue: "
    )

    if confirmation == "DELETE ROOMS":
        db.query(Allocation).delete(synchronize_session=False)
        db.query(Resource).delete(synchronize_session=False)

        db.commit()

        print("\nROOM CLEANUP SUCCESSFUL")
        print("Remaining rooms:", db.query(Resource).count())
        print("Remaining allocations:", db.query(Allocation).count())
        print("Students preserved:", "Yes")
        print("Examinations preserved:", "Yes")
    else:
        print("Operation cancelled.")

except Exception as error:
    db.rollback()
    print("Cleanup failed:", error)

finally:
    db.close()
