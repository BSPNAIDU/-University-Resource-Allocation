def greedy_allocate(students, rooms):
    """
    Assign students to available rooms using a Greedy approach.
    """

    allocations = []
    student_index = 0

    for room in rooms:
        if room.is_available == False:
            continue

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

    if student_index < len(students):
        raise ValueError(
            f"Insufficient room capacity: "
            f"{len(students) - student_index} student(s) could not be allocated."
        )

    return allocations
