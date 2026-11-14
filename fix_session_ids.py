from pathlib import Path
import re

path = Path("frontend/pages/4_Seat_Allocation.py")
lines = path.read_text(encoding="utf-8-sig").splitlines()

# Find the line that loads examination sessions.
index = None
variable = None

for i, line in enumerate(lines):
    if "/allocations/sessions" in line:
        match = re.search(r"(\w+)\s*=", line)
        if match:
            index = i
            variable = match.group(1)
            break

if index is None:
    print("Session-loading statement not found. No changes made.")
    raise SystemExit(1)

# Avoid inserting the normalization twice.
if any("SESSION_ID_NORMALIZATION" in line for line in lines):
    print("Session ID normalization already exists.")
else:
    code = [
        "",
        "    # SESSION_ID_NORMALIZATION",
        f"    if isinstance({variable}, dict):",
        f"        {variable} = {variable}.get('sessions', [])",
        f"    {variable} = [",
        f"        {{**s, 'session_id': s.get('session_id') or s.get('id')}}",
        f"        for s in ({variable} or [])",
        f"        if isinstance(s, dict) and (s.get('session_id') or s.get('id'))",
        "    ]",
        ""
    ]

    indent = re.match(r"\s*", lines[index]).group(0)
    code = [
        (indent + line if line else "")
        for line in code
    ]

    lines[index + 1:index + 1] = code
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SUCCESS: Normalized session IDs in {variable}.")

