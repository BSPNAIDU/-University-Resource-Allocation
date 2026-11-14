from pathlib import Path

path = Path("backend/app/api/routes/students.py")
content = path.read_text(encoding="utf-8-sig")

old = "year = int(float(year_value))"

new = """year_text = str(year_value).strip().lower()

                year_words = {
                    "first year": 1, "first": 1,
                    "second year": 2, "second": 2,
                    "third year": 3, "third": 3,
                    "fourth year": 4, "fourth": 4
                }

                if year_text in year_words:
                    year = year_words[year_text]
                else:
                    year_text = year_text.replace(" year", "").strip()

                    for suffix in ["st", "nd", "rd", "th"]:
                        if year_text.endswith(suffix):
                            year_text = year_text[:-2]
                            break

                    year = int(float(year_text))"""

if old not in content:
    print("ERROR: Original year conversion line not found. No changes made.")
    raise SystemExit(1)

content = content.replace(old, new, 1)
path.write_text(content, encoding="utf-8")

print("SUCCESS: Student year validation updated.")
