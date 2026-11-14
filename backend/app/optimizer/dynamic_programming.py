def dynamic_programming_allocate(students, rooms):
    """
    Dynamic Programming:
    1. Minimize the number of rooms.
    2. Minimize unused room capacity when room count is equal.
    """

    student_count = len(students)

    available_rooms = [
        room for room in rooms
        if room.is_available == True and room.capacity > 0
    ]

    if student_count == 0:
        return []

    # Each state stores (selected room indices, actual total capacity).
    dp = [None] * (student_count + 1)
    dp[0] = ([], 0)

    for room_index, room in enumerate(available_rooms):
        for required in range(student_count, 0, -1):
            previous_required = max(0, required - room.capacity)
            previous = dp[previous_required]

            if previous is None:
                continue

            selected_indices = previous[0] + [room_index]
            total_capacity = previous[1] + room.capacity
            candidate = (selected_indices, total_capacity)

            current = dp[required]

            if current is None or (
                len(candidate[0]), candidate[1]
            ) < (
                len(current[0]), current[1]
            ):
                dp[required] = candidate

    if dp[student_count] is None:
        raise ValueError(
            "No combination of available rooms can accommodate all students."
        )

    selected_indices = dp[student_count][0]

    selected_rooms = [
        available_rooms[index] for index in selected_indices
    ]

    allocations = []
    student_index = 0

    for room in selected_rooms:
        for seat_number in range(1, room.capacity + 1):
            if student_index >= student_count:
                break

            student = students[student_index]

            allocations.append({
                "student_id": student.id,
                "resource_id": room.id,
                "seat_number": f"S{seat_number:02d}"
            })

            student_index += 1

    return allocations
