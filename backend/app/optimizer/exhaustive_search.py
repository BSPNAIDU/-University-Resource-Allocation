from itertools import combinations


def exhaustive_search_allocate(students, rooms):
    student_count = len(students)

    if student_count == 0:
        return []

    available_rooms = [
        room for room in rooms
        if room.is_available == True and room.capacity > 0
    ]

    if len(available_rooms) > 20:
        raise ValueError(
            "Exhaustive Search supports a maximum of 20 available rooms."
        )

    selected_rooms = None

    # Test combinations using the minimum number of rooms first.
    for room_count in range(1, len(available_rooms) + 1):
        feasible_combinations = []

        for room_combination in combinations(available_rooms, room_count):
            total_capacity = sum(
                room.capacity for room in room_combination
            )

            if total_capacity >= student_count:
                feasible_combinations.append(
                    (total_capacity, room_combination)
                )

        if feasible_combinations:
            # Select the combination with minimum unused capacity.
            feasible_combinations.sort(key=lambda item: item[0])
            selected_rooms = feasible_combinations[0][1]
            break

    if selected_rooms is None:
        raise ValueError(
            "No combination of available rooms can accommodate all students."
        )

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
