from pathlib import Path

# Fix frontend session ID lookup
frontend = Path("frontend/pages/4_Seat_Allocation.py")
content = frontend.read_text(encoding="utf-8-sig")

content = content.replace(
    'session_id = session.get("id")',
    'session_id = session.get("session_id") or session.get("id")'
)

frontend.write_text(content, encoding="utf-8")

# Add explicit session and examination IDs to backend response
backend = Path("backend/app/api/routes/allocations.py")
content = backend.read_text(encoding="utf-8-sig")

old = '''        result.append({
            "session_id": session.id,
            "exam_code": exam.exam_code if exam else "",'''

new = '''        result.append({
            "id": session.id,
            "session_id": session.id,
            "examination_id": exam.id if exam else None,
            "exam_code": exam.exam_code if exam else "",'''

if old in content:
    content = content.replace(old, new, 1)
    backend.write_text(content, encoding="utf-8")
    print("Backend session response corrected.")
else:
    print("Backend response already updated or pattern not found.")

print("Frontend session ID lookup corrected.")
