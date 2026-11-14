from pathlib import Path
import re

files = [
    Path("frontend/pages/4_Seat_Allocation.py"),
    Path("frontend/pages/5_Seat_Allocation.py"),
    Path("backend/app/api/routes/allocations.py"),
]

for path in files:
    if not path.exists():
        continue

    print("\n" + "=" * 65)
    print("FILE:", path)
    print("=" * 65)

    lines = path.read_text(encoding="utf-8-sig").splitlines()

    for number, line in enumerate(lines, 1):
        if re.search(
            r"requests\.|API_URL|api_url|allocations|@router\.(get|post|put|delete)|Not Found",
            line,
            re.I
        ):
            print(f"{number}: {line.strip()}")
