from pathlib import Path

root = Path("backend/app")

for path in root.rglob("*.py"):
    if path.name == "__init__.py":
        continue

    content = path.read_text(encoding="utf-8-sig")
    if "Year must be a number" in content:
        print("\nFILE:", path)
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if "Year must be a number" in line:
                start = max(0, i - 12)
                end = min(len(lines), i + 5)

                for j in range(start, end):
                    print(f"{j + 1}: {lines[j]}")
