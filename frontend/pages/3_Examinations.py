import streamlit as st
from styles import load_css
import pandas as pd
from api_client import api_get, get_error_message

st.set_page_config(page_title="Examinations", page_icon="📝", layout="wide")

load_css()
st.title("📝 Examination Management")

try:
    exams = api_get("/examinations/")
    conflicts = api_get("/conflicts/")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Examinations", len(exams))
    c2.metric("Student Conflicts", conflicts.get("student_conflict_count", 0))
    c3.metric("Room Conflicts", conflicts.get("room_conflict_count", 0))

    st.subheader("Examination Schedule")

    if exams:
        df = pd.DataFrame(exams)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No examinations found.")

    st.divider()
    st.subheader("Schedule Conflict Details")

    student_conflicts = conflicts.get("student_conflicts", [])
    room_conflicts = conflicts.get("room_conflicts", [])

    if student_conflicts:
        st.warning("Student schedule conflicts")
        st.dataframe(
            pd.DataFrame(student_conflicts),
            use_container_width=True,
            hide_index=True
        )

    if room_conflicts:
        st.warning("Room schedule conflicts")
        st.dataframe(
            pd.DataFrame(room_conflicts),
            use_container_width=True,
            hide_index=True
        )

    if not student_conflicts and not room_conflicts:
        st.success("No schedule conflicts detected.")

except Exception as e:
    st.error(get_error_message(e))
