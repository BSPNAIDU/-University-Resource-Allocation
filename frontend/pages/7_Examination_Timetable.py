from io import BytesIO

import pandas as pd
import streamlit as st

from api_client import api_get, api_post, get_error_message

st.set_page_config(
    page_title="Examination Timetable",
    page_icon="📅",
    layout="wide"
)

st.title("📅 Examination Timetable")
st.caption("Upload the complete university examination schedule in one Excel file.")

if not st.session_state.get("authenticated", False):
    st.warning("Please log in to continue.")
    st.stop()

template_data = pd.DataFrame([
    {
        "Subject Code": "CS101",
        "Subject Name": "Java Programming",
        "Exam Date": "2026-11-15",
        "Start Time": "09:00",
        "End Time": "12:00",
        "Department": "CSE",
    },
    {
        "Subject Code": "CS102",
        "Subject Name": "Database Management",
        "Exam Date": "2026-11-15",
        "Start Time": "14:00",
        "End Time": "17:00",
        "Department": "CSE",
    },
])

buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    template_data.to_excel(
        writer,
        index=False,
        sheet_name="Examination Timetable"
    )

st.download_button(
    "⬇️ Download Timetable Excel Template",
    data=buffer.getvalue(),
    file_name="examination_timetable_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.divider()

st.subheader("Upload Examination Timetable")

st.info(
    "Required columns: Subject Code, Subject Name, Exam Date, "
    "Start Time and End Time. Department is optional."
)

uploaded_file = st.file_uploader(
    "Select your completed timetable Excel or CSV file",
    type=["xlsx", "csv"],
    key="timetable_file"
)

if uploaded_file is not None:
    try:
        file_bytes = uploaded_file.getvalue()

        if uploaded_file.name.lower().endswith(".csv"):
            preview_df = pd.read_csv(BytesIO(file_bytes))
        else:
            preview_df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")

        st.subheader("Timetable Preview")
        st.metric("Total Timetable Rows", len(preview_df))
        st.dataframe(preview_df.head(20), use_container_width=True)

        if st.button("Import Examination Timetable", type="primary"):
            with st.spinner("Validating and importing examination timetable..."):
                response = api_post(
                    "/examinations/upload-timetable",
                    files={
                        "file": (
                            uploaded_file.name,
                            file_bytes,
                            uploaded_file.type or "application/octet-stream"
                        )
                    }
                )

            st.success("Examination timetable imported successfully!")
            st.json(response)

            st.session_state.pop("timetable_file", None)

    except Exception as error:
        st.error(get_error_message(error))

st.divider()
st.subheader("Saved Examination Timetable")

if st.button("Refresh Examination Timetable"):
    st.rerun()

try:
    examinations = api_get("/examinations/")

    if isinstance(examinations, list):
        st.metric("Saved Examinations", len(examinations))

        if examinations:
            display_df = pd.DataFrame(examinations)

            if "duration_minutes" in display_df.columns:
                display_df["duration_minutes"] = (
                    display_df["duration_minutes"].astype(str) + " minutes"
                )

            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No examination timetable has been uploaded yet.")
    else:
        st.write(examinations)

except Exception as error:
    st.error(get_error_message(error))
