from collections import Counter

def valid_at(grid, r, c, branch):
    # Only horizontal and vertical adjacency are restricted; diagonals are allowed.
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < len(grid) and 0 <= nc < len(grid[0]):
            other = grid[nr][nc]
            if other is not None and other["branch"] == branch:
                return False
    return True

def generate(students, rooms, search_budget=150000):
    total_capacity = sum(min(r.capacity, r.rows * r.columns) for r in rooms)
    if len(students) > total_capacity:
        raise ValueError(f"Not enough seats: {len(students)} students but only {total_capacity} usable seats.")

    # Place the most frequent branches first, with round-robin ordering inside each branch.
    groups = {}
    for s in students:
        groups.setdefault(s.branch, []).append(s)
    ordered = []
    while any(groups.values()):
        for branch in sorted(groups, key=lambda b: (-len(groups[b]), b)):
            if groups[branch]:
                ordered.append(groups[branch].pop(0))

    seats = []
    for room in rooms:
        cap = min(room.capacity, room.rows * room.columns)
        count = 0
        for r in range(room.rows):
            for c in range(room.columns):
                if count >= cap:
                    break
                seats.append((room, r, c))
                count += 1
            if count >= cap:
                break

    # Backtracking across physical seats. Branch ordering helps find a valid arrangement quickly.
    grid_by_room = {r.id: [[None for _ in range(r.columns)] for _ in range(r.rows)] for r in rooms}
    chosen = [None] * len(seats)
    nodes = 0

    def search(i):
        nonlocal nodes
        nodes += 1
        if nodes > search_budget:
            return False
        if i == len(students):
            return True
        student = ordered[i]
        # Try seats in stable order, preferring rooms that already contain other branches.
        for j, (room, rr, cc) in enumerate(seats):
            if chosen[j] is not None:
                continue
            grid = grid_by_room[room.id]
            if valid_at(grid, rr, cc, student.branch):
                chosen[j] = student
                grid[rr][cc] = {"branch": student.branch, "student": student}
                if search(i + 1):
                    return True
                grid[rr][cc] = None
                chosen[j] = None
        return False

    # A fast branch-balanced greedy attempt first, then bounded backtracking.
    # Backtracking is used directly for reliable constraint validation on hackathon-sized datasets.
    if not search(0):
        raise ValueError("Could not find a valid seating arrangement within the search limit. Try adding rooms, increasing capacity, or changing the room layout.")

    result = []
    for (room, rr, cc), student in zip(seats, chosen):
        if student is not None:
            result.append({"student": student, "room": room, "row": rr + 1, "column": cc + 1,
                           "seat_number": f"R{rr+1}-C{cc+1}"})
    violations = validate(result)
    if violations:
        raise ValueError(f"Internal validation found {len(violations)} adjacency violations; plan was not saved.")
    return result

def validate(assignments):
    by_room = {}
    for a in assignments:
        key = a["room"].id
        by_room.setdefault(key, {})[(a["row"], a["column"])] = a["student"].branch
    issues = []
    for room_id, seats in by_room.items():
        for (r, c), branch in seats.items():
            for pos in ((r+1, c), (r, c+1)):
                if seats.get(pos) == branch:
                    issues.append({"room_id": room_id, "row": r, "column": c, "branch": branch})
    return issues
