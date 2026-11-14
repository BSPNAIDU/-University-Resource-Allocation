import streamlit as st
import pandas as pd

from styles import load_css
from api_client import api_get, get_error_message

st.set_page_config(page_title="Reallocation", page_icon="🔄", layout="wide")
load_css()

st.title("🔄 Dynamic Seat Reallocation")
st.caption(
    "Reallocation is triggered automatically when an allocated classroom "
    "is marked unavailable in Block and Classroom Management."
)

try:
    sessions = api_get("/allocations/sessions")
    if isinstance(sessions, dict):
        sessions = sessions.get("sessions", [])
    sessions = sessions or []

    if not sessions:
        st.info("No examination sessions are available.")
        st.stop()

    rows = []
    for session in sessions:
        rows.append({
            "Session ID": session.get("session_id", session.get("id")),
            "Subject Code": session.get("exam_code"),
            "Subject": session.get("subject_name"),
            "Session": session.get("session_name"),
            "Date": session.get("exam_date"),
            "Start Time": session.get("start_time"),
            "Registered": session.get("registered_students", 0),
            "Allocated": session.get("allocated_students", 0),
        })

    st.subheader("Session-wise Allocation Status")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Reallocation procedure")
    st.markdown(
        """
        1. Open **Block and Classroom Management**.
        2. Select the classroom that has become unavailable.
        3. Turn off **Classroom Available** and save the change.
        4. The backend identifies affected allocations by examination session.
        5. Only affected students are moved to free seats in available rooms.
        6. If sufficient seats are not available, the transaction is rolled back
           and the original allocations and room status are preserved.
        """
    )

    st.info(
        "The room availability update performs reallocation automatically. "
        "There is no separate examination-level reallocation request because "
        "students must be handled by their actual session."
    )

    if st.button("Refresh Reallocation Status", type="primary"):
        st.rerun()

except Exception as error:
    st.error(get_error_message(error))
