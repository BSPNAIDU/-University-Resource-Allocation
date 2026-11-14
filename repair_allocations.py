from pathlib import Path

path = Path("backend/app/api/routes/allocations.py")
content = path.read_text(encoding="utf-8-sig")

lines = content.splitlines()
fixed_lines = []

for line in lines:
    if line.strip() == r"\n":
        continue
    fixed_lines.append(line)

path.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")

print("Removed the accidental literal newline.")
