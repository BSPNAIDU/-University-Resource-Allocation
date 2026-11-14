def reallocate_students(students, rooms):
    """
    Allocate students to available rooms after a room disruption.
    Returns a new allocation list without modifying the database.
    """

    available_rooms = [
        room for room in rooms
        if room.is_available == True and room.capacity > 0
    ]

    total_capacity = sum(room.capacity for room in available_rooms)

    if total_capacity < len(students):
        raise ValueError(
            f"Insufficient available capacity. "
            f"Required: {len(students)}, Available: {total_capacity}."
        )

    allocations = []
    student_index = 0

    for room in available_rooms:
        for seat_number in range(1, room.capacity + 1):
            if student_index >= len(students):
                return allocations

            student = students[student_index]

            allocations.append({
                "student_id": student.id,
                "resource_id": room.id,
                "seat_number": f"S{seat_number:02d}"
            })

            student_index += 1

    return allocations
