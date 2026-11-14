import streamlit as st
import pandas as pd
import plotly.express as px

from styles import load_css
from api_client import (
    api_get,
    api_register,
    api_login,
    api_logout,
    get_error_message
)

st.set_page_config(
    page_title="University Resource Allocation",
    page_icon="??",
    layout="wide"
)

load_css()


def show_authentication():
    st.markdown(
        """
        <div class="portal-banner">
            <h1>University Examination Portal</h1>
            <p>Smart Resource Allocation and Examination Seating Management</p>
            <p>Secure multi-university platform for faculty operations</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.title("Welcome to University Resource Allocation")

    login_tab, register_tab = st.tabs(["University Login", "Register University"])

    with login_tab:
        st.subheader("University Login")

        with st.form("login_form"):
            university_code = st.text_input(
                "University Code",
                placeholder="Enter university code"
            )

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

            if submitted:
                if university_code.strip() == "" or password == "":
                    st.error("Please enter your university code and password.")
                else:
                    try:
                        result = api_login(
                            university_code.strip(),
                            password
                        )

                        st.success(
                            f"Welcome, {result['university']['university_name']}!"
                        )
                        st.rerun()

                    except Exception as error:
                        st.error(get_error_message(error))

    with register_tab:
        st.subheader("Register Your University")

        with st.form("register_form"):
            university_name = st.text_input(
                "University Name",
                placeholder="Enter university name"
            )

            university_code = st.text_input(
                "University Code",
                placeholder="Create a unique university code"
            )

            password = st.text_input(
                "Create Password",
                type="password"
            )

            address = st.text_input("Address")
            city = st.text_input("City")
            state = st.text_input("State")

            submitted = st.form_submit_button(
                "Register University",
                use_container_width=True
            )

            if submitted:
                if not university_name.strip() or not university_code.strip() or not password:
                    st.error("University name, code and password are required.")
                elif len(password) < 8:
                    st.error("Password must contain at least 8 characters.")
                else:
                    try:
                        result = api_register({
                            "university_name": university_name.strip(),
                            "university_code": university_code.strip(),
                            "password": password,
                            "address": address.strip() or None,
                            "city": city.strip() or None,
                            "state": state.strip() or None
                        })

                        st.success(
                            f"{result['university_name']} registered successfully!"
                        )
                        st.info(
                            "Your university is registered. Please log in using your university code and password."
                        )

                    except Exception as error:
                        st.error(get_error_message(error))


def show_dashboard():
    university = st.session_state.get("university", {})

    st.sidebar.title("University Portal")
    st.sidebar.success(
        university.get("university_name", "University")
    )
    st.sidebar.caption(
        f"University Code: {university.get('university_code', '')}"
    )
    st.sidebar.caption("Backend API: http://127.0.0.1:8000")

    if st.sidebar.button("Refresh Dashboard", use_container_width=True):
        st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        api_logout()
        st.rerun()

    st.markdown(
        f"""
        <div class="portal-banner">
            <h1>University Examination Dashboard</h1>
            <p>{university.get('university_name', 'University')}</p>
            <p>Smart Resource Allocation and Examination Seating Management</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        data = api_get("/dashboard/")

        overview = data.get("overview", {})
        rooms = data.get("room_statistics", {})
        conflicts = data.get("conflict_statistics", {})

        st.subheader("University Overview")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total Students",
            overview.get("total_students", 0)
        )

        c2.metric(
            "Total Examinations",
            overview.get("total_examinations", 0)
        )

        c3.metric(
            "Total Rooms",
            overview.get("total_rooms", 0)
        )

        c4.metric(
            "Total Allocations",
            overview.get("total_allocations", 0)
        )

        c5, c6, c7, c8 = st.columns(4)

        c5.metric(
            "Available Rooms",
            rooms.get("available_rooms", 0)
        )

        c6.metric(
            "Unavailable Rooms",
            rooms.get("unavailable_rooms", 0)
        )

        c7.metric(
            "Registered Students",
            overview.get("total_registrations", 0)
        )

        c8.metric(
            "Allocation Progress",
            f"{overview.get('allocation_percentage', 0)}%"
        )

        st.divider()

        left, right = st.columns(2)

        with left:
            st.subheader("Room Availability")

            available = rooms.get("available_rooms", 0)
            unavailable = rooms.get("unavailable_rooms", 0)

            if available + unavailable > 0:
                room_chart = pd.DataFrame({
                    "Status": ["Available", "Unavailable"],
                    "Rooms": [available, unavailable]
                })

                fig = px.pie(
                    room_chart,
                    names="Status",
                    values="Rooms",
                    hole=0.45,
                    title="Room Availability Distribution"
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No examination rooms have been registered.")

        with right:
            st.subheader("Examination Distribution")

            departments = data.get("department_distribution", {})

            if departments:
                dept_df = pd.DataFrame(
                    list(departments.items()),
                    columns=["Department", "Examinations"]
                )

                fig = px.bar(
                    dept_df,
                    x="Department",
                    y="Examinations",
                    title="Examinations by Department"
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No examination records available.")

        st.divider()

        st.subheader("Recent Examination Schedule")

        recent_exams = data.get("recent_examinations", [])

        if recent_exams:
            exam_df = pd.DataFrame(recent_exams)

            st.dataframe(
                exam_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No examinations have been added yet.")

        st.subheader("Conflict Detection Summary")

        total_conflicts = conflicts.get("total_conflicts", 0)

        if total_conflicts == 0:
            st.success("No schedule conflicts detected.")
        else:
            st.warning(f"{total_conflicts} conflict(s) detected.")

            col1, col2 = st.columns(2)

            col1.metric(
                "Student Conflicts",
                conflicts.get("student_conflict_count", 0)
            )

            col2.metric(
                "Room Conflicts",
                conflicts.get("room_conflict_count", 0)
            )

        st.divider()

        st.subheader("Allocation Performance")

        st.progress(
            min(
                max(
                    float(overview.get("allocation_percentage", 0)) / 100,
                    0.0
                ),
                1.0
            )
        )

        st.caption(
            f"{overview.get('allocation_percentage', 0)}% of registered examination entries have been allocated."
        )

    except Exception as error:
        st.error("Could not load university dashboard data.")

        st.code(get_error_message(error))

        st.info(
            "Check that the FastAPI backend is running and your login session is valid."
        )


if st.session_state.get("authenticated", False):
    show_dashboard()
else:
    show_authentication()
