from pathlib import Path
import re

path = Path("frontend/pages/4_Seat_Allocation.py")
content = path.read_text(encoding="utf-8-sig")

# Correct the session dropdown to use the actual session ID.
content = re.sub(
    r'options\s*=\s*\{.*?\n\s*for\s+s\s+in\s+sessions\s*\}',
    '''options = {
        f"Session {s.get('session_id') or s.get('id')} | Examination {s.get('examination_id') or s.get('exam_id')} | {s.get('exam_date')} | {s.get('start_time')}":
        (s.get('session_id') or s.get('id'))
        for s in sessions
        if s.get('session_id') or s.get('id')
    }''',
    content,
    count=1,
    flags=re.S
)

# Normalize session identifiers before the dropdown is constructed.
marker = "# SESSION_ID_NORMALIZATION"

if marker not in content:
    print("Session normalization marker missing. No further changes made.")
    raise SystemExit(1)

# Make sure the selected session is never submitted as None.
content = content.replace(
    'result = api_get(f"/allocations/session/{options[selected]}")',
    '''selected_session_id = options[selected]
        if selected_session_id is None:
            st.error("Session ID is missing from the backend response.")
            st.stop()

        result = api_get(f"/allocations/session/{selected_session_id}")'''
)

path.write_text(content, encoding="utf-8")
print("Updated session dropdown and allocation lookup.")

