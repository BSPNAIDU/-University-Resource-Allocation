from pathlib import Path
import re

root = Path("frontend")

for path in root.rglob("*.py"):
    if "pages" in path.parts:
        continue

    content = path.read_text(encoding="utf-8-sig")

    if re.search(r"def\s+(api_get|api_post)\s*\(", content):
        print("\nFOUND:", path)
        for number, line in enumerate(content.splitlines(), 1):
            if re.search(r"def\s+(api_get|api_post)\s*\(", line):
                print(f"{number}: {line.strip()}")

