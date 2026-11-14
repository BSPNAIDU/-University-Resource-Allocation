from io import BytesIO

import pandas as pd
import streamlit as st

from api_client import api_get, api_post, get_error_message


st.set_page_config(
    page_title="Student Management",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Details Management")
st.caption("Upload and manage your university student records.")

if not st.session_state.get("authenticated", False):
    st.warning("Please log in to continue.")
    st.stop()


# ==========================================
# DOWNLOAD FIXED EXCEL TEMPLATE
# ==========================================

st.subheader("1. Download Student Excel Template")

template_columns = [
    "Register Number",
    "Student Name",
    "Department",
    "Year"
]

template_df = pd.DataFrame(columns=template_columns)

template_buffer = BytesIO()

with pd.ExcelWriter(template_buffer, engine="openpyxl") as writer:
    template_df.to_excel(
        writer,
        index=False,
        sheet_name="Student Details"
    )

    worksheet = writer.sheets["Student Details"]
    worksheet.freeze_panes = "A2"

    for column, width in {
        "A": 22,
        "B": 28,
        "C": 18,
        "D": 12
    }.items():
        worksheet.column_dimensions[column].width = width

st.download_button(
    label="📥 Download Student Excel Template",
    data=template_buffer.getvalue(),
    file_name="Student_Details_Template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary"
)

st.info(
    "Required columns: Register Number, Student Name, Department and Year. "
    "No manual column mapping is required."
)


# ==========================================
# STUDENT UPLOAD
# ==========================================

st.divider()
st.subheader("2. Upload Student Details")

uploaded_file = st.file_uploader(
    "Choose your student Excel or CSV file",
    type=["xlsx", "xls", "csv"],
    key="student_details_upload"
)

if uploaded_file is not None:

    st.success(f"Selected file: {uploaded_file.name}")

    try:
        file_bytes = uploaded_file.getvalue()

        if uploaded_file.name.lower().endswith(".csv"):
            preview_df = pd.read_csv(BytesIO(file_bytes))
        else:
            preview_df = pd.read_excel(BytesIO(file_bytes))

        st.write("Uploaded data preview")
        st.dataframe(
            preview_df.head(10),
            use_container_width=True
        )

        st.metric("Total Rows in File", len(preview_df))

        if st.button("Upload Student Records", type="primary"):

            with st.spinner("Validating and uploading student records..."):

                response = api_post(
                    "/students/upload",
                    files={
                        "file": (
                            uploaded_file.name,
                            file_bytes,
                            uploaded_file.type or "application/octet-stream"
                        )
                    }
                )

            st.success("Student upload completed!")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Total Rows", response.get("total_rows", 0))
            col2.metric("Inserted", response.get("inserted", 0))
            col3.metric("Duplicates Skipped", response.get("duplicates_skipped", 0))
            col4.metric("Invalid Rows", response.get("invalid_rows", 0))

            errors = response.get("errors", [])

            if errors:
                with st.expander("View validation errors"):
                    for error in errors:
                        st.warning(error)

            st.session_state["refresh_students"] = True

    except Exception as error:
        st.error(get_error_message(error))


# ==========================================
# SAVED STUDENT RECORDS
# ==========================================

st.divider()
st.subheader("3. Current University Student Records")

if st.button("🔄 Refresh Student Records"):
    st.session_state["refresh_students"] = True

try:
    students = api_get("/students/")

    if isinstance(students, list):

        st.metric("Total Students", len(students))

        if students:

            students_df = pd.DataFrame(students)

            display_columns = [
                "student_number",
                "full_name",
                "department",
                "year_of_study",
                "is_active"
            ]

            display_columns = [
                column for column in display_columns
                if column in students_df.columns
            ]

            st.dataframe(
                students_df[display_columns],
                use_container_width=True,
                hide_index=True
            )

            csv_data = students_df[display_columns].to_csv(index=False)

            st.download_button(
                "📥 Download Saved Student Records",
                data=csv_data,
                file_name="University_Student_Records.csv",
                mime="text/csv"
            )

        else:
            st.info("No student records found for this university.")

    else:
        st.error(students)

except Exception as error:
    st.error(get_error_message(error))
