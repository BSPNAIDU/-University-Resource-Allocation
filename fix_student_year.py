from pathlib import Path
import re

root = Path("backend/app")
matches = []

for path in root.rglob("*.py"):
    if path.name == "__init__.py":
        continue
    content = path.read_text(encoding="utf-8-sig")
    if "Year must be a number" in content:
        matches.append((path, content))

if not matches:
    print("Could not locate the student year validation.")
    raise SystemExit(1)

helper = '''

def normalize_student_year(value):
    import re

    if value is None:
        return None

    text = str(value).strip().lower()
    mapping = {
        "first year": 1, "1st year": 1, "first": 1,
        "second year": 2, "2nd year": 2, "second": 2,
        "third year": 3, "3rd year": 3, "third": 3,
        "fourth year": 4, "4th year": 4, "fourth": 4,
    }

    if text in mapping:
        return mapping[text]

    match = re.search(r"\\\\b([1-4])\\\\b", text)
    if match:
        return int(match.group(1))

    try:
        number = int(float(text))
        if number in (1, 2, 3, 4):
            return number
    except (ValueError, TypeError):
        pass

    return None

'''

for path, content in matches:
    if "def normalize_student_year(" not in content:
        # Add helper after imports, before the first route/function.
        positions = [
            m.start() for m in re.finditer(r"^(?:@router\\.|def |async def )", content, re.M)
        ]
        if not positions:
            print(f"Could not safely insert helper into {path}")
            continue

        position = positions[0]
        content = content[:position] + helper + "\\n" + content[position:]

    # Normalize the year value immediately before the existing numeric check.
    lines = content.splitlines()
    changed = False

    for i, line in enumerate(lines):
        if "Year must be a number" not in line:
            continue

        indent = re.match(r"\\s*", line).group(0)

        # Use the current row's year value where the validation refers to it.
        # This supports common row-based validation patterns.
        for j in range(max(0, i - 8), i):
            if re.search(r"\\byear\\s*=", lines[j], re.I):
                lines.insert(j, indent + "# Normalize text year values before validation")
                lines.insert(j + 1, indent + "year = normalize_student_year(year)")
                changed = True
                break

    if changed:
        path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        print(f"Updated: {path}")
    else:
        print(f"Helper added where possible; validation needs a targeted edit: {path}")

