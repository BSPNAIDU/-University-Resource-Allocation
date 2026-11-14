from pathlib import Path
import re

path = Path("frontend/pages/4_Seat_Allocation.py")
lines = path.read_text(encoding="utf-8-sig").splitlines()

# Remove the previously inserted incorrect block.
start = next(
    (i for i, line in enumerate(lines)
     if "SESSION_ID_NORMALIZATION" in line),
    None
)

if start is not None:
    end = start + 1
    while end < len(lines):
        if lines[end].strip() == "]":
            end += 1
            break
        end += 1
    del lines[start:end]

# Find the session API response assignment.
index = next(
    (i for i, line in enumerate(lines)
     if "/allocations/sessions" in line and "=" in line),
    None
)

if index is None:
    print("Session API line not found. File not changed further.")
    raise SystemExit(1)

base = re.match(r"^\s*", lines[index]).group(0)

block = [
    base + "# SESSION_ID_NORMALIZATION",
    base + "if isinstance(response, dict):",
    base + "    response = response.get('sessions', [])",
    base + "sessions = [",
    base + "    {**s, 'session_id': s.get('session_id') or s.get('id')}",
    base + "    for s in (response or [])",
    base + "    if isinstance(s, dict) and (s.get('session_id') or s.get('id'))",
    base + "]",
]

lines[index + 1:index + 1] = block
path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("Session ID code repaired.")
