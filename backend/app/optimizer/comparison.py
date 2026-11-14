from time import perf_counter

from backend.app.optimizer.greedy import greedy_allocate
from backend.app.optimizer.dynamic_programming import dynamic_programming_allocate
from backend.app.optimizer.exhaustive_search import exhaustive_search_allocate


def measure_algorithm(algorithm, students, rooms):
    start_time = perf_counter()

    try:
        allocations = algorithm(students, rooms)
        execution_time = (perf_counter() - start_time) * 1000

        total_students = len(students)
        allocated_students = len(allocations)

        room_ids = set(
            item["resource_id"] for item in allocations
        )

        selected_rooms = [
            room for room in rooms
            if room.id in room_ids
        ]

        total_capacity = sum(
            room.capacity for room in selected_rooms
        )

        utilization = (
            allocated_students / total_capacity * 100
            if total_capacity > 0 else 0
        )

        return {
            "status": (
                "success"
                if allocated_students == total_students
                else "incomplete"
            ),
            "execution_time_ms": round(execution_time, 4),
            "total_students": total_students,
            "allocated_students": allocated_students,
            "rooms_used": len(room_ids),
            "selected_room_capacity": total_capacity,
            "room_utilization_percentage": round(utilization, 2),
            "allocations": allocations,
        }

    except Exception as error:
        execution_time = (perf_counter() - start_time) * 1000

        return {
            "status": "failed",
            "execution_time_ms": round(execution_time, 4),
            "total_students": len(students),
            "allocated_students": 0,
            "rooms_used": 0,
            "selected_room_capacity": 0,
            "room_utilization_percentage": 0,
            "error": str(error),
            "allocations": [],
        }


def compare_algorithms(students, rooms):

    results = {
        "Greedy": measure_algorithm(
            greedy_allocate, students, rooms
        ),
        "Dynamic Programming": measure_algorithm(
            dynamic_programming_allocate, students, rooms
        ),
        "Exhaustive Search": measure_algorithm(
            exhaustive_search_allocate, students, rooms
        ),
    }

    successful_results = {
        name: result
        for name, result in results.items()
        if result["status"] == "success"
    }

    best_algorithm = None

    if successful_results:
        best_algorithm = max(
            successful_results,
            key=lambda name: (
                -successful_results[name]["rooms_used"],
                successful_results[name]["room_utilization_percentage"],
                -successful_results[name]["execution_time_ms"],
            ),
        )

    return {
        "comparison": results,
        "recommended_algorithm": best_algorithm,
        "selection_criteria": (
            "Successful allocation, minimum rooms, maximum room "
            "utilization, then execution time."
        ),
    }
