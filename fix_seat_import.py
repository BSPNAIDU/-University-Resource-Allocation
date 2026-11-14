from pathlib import Path

path = Path("frontend/pages/4_Seat_Allocation.py")
content = path.read_text(encoding="utf-8-sig")

content = content.replace(
    "from frontend.utils.api import api_get, api_post",
    "from frontend.api_client import api_get, api_post"
)

path.write_text(content, encoding="utf-8")

print("Seat Allocation API import corrected.")
