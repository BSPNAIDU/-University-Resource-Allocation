import streamlit as st
import pandas as pd
import requests
from datetime import datetime

from frontend.api_client import (
    api_get,
    api_post,
    get_error_message,
    API_BASE_URL,
    get_auth_headers,
)

st.set_page_config(page_title="Seat Allocation", layout="wide")
st.title("Seat Allocation")
st.write("Generate and monitor examination seating allocations.")

try:
    response = api_get("/allocations/sessions")
    if isinstance(response, dict):
        sessions = response.get("sessions", [])
    else:
        sessions = response or []

    sessions = [
        {**item, "session_id": item.get("session_id") or item.get("id")}
        for item in sessions
        if isinstance(item, dict) and (item.get("session_id") or item.get("id"))
    ]

    if not sessions:
        st.warning("No examination sessions found. Upload the timetable first.")
        st.stop()

    st.subheader("Examination Sessions")
    session_rows = []
    for session in sessions:
        session_rows.append({
            "Session ID": session.get("session_id"),
            "Examination ID": session.get("examination_id"),
            "Subject": session.get("exam_code"),
            "Session": session.get("session_name"),
            "Date": session.get("exam_date"),
            "Start Time": session.get("start_time"),
            "Capacity": session.get("capacity"),
            "Registered Students": session.get("registered_students", 0),
            "Allocated Students": session.get("allocated_students", 0),
        })
    st.dataframe(pd.DataFrame(session_rows), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Generate Seating Allocations")

    if st.button("Generate All Sessions", type="primary", use_container_width=True):
        generated = 0
        skipped = 0
        failed = []
        progress = st.progress(0)
        status = st.empty()

        for index, session in enumerate(sessions):
            session_id = session["session_id"]
            try:
                existing = api_get(f"/allocations/session/{session_id}")
                existing_allocations = (
                    existing.get("allocations", [])
                    if isinstance(existing, dict) else existing or []
                )
                if existing_allocations:
                    skipped += 1
                else:
                    api_post(f"/allocations/generate-session/{session_id}")
                    generated += 1
            except Exception as error:
                failed.append({"session_id": session_id, "error": get_error_message(error)})

            progress.progress((index + 1) / len(sessions))
            status.write(f"Processing session {index + 1} of {len(sessions)}")

        st.session_state["allocation_results"] = {
            "generated": generated,
            "skipped": skipped,
            "failed": failed,
        }
        st.rerun()

    results = st.session_state.get("allocation_results")
    if results:
        st.divider()
        st.subheader("Generation Results")
        col1, col2, col3 = st.columns(3)
        col1.metric("Generated Sessions", results["generated"])
        col2.metric("Existing Sessions Skipped", results["skipped"])
        col3.metric("Failed Sessions", len(results["failed"]))
        if results["failed"]:
            st.error("Some sessions could not be allocated.")
            st.dataframe(pd.DataFrame(results["failed"]), use_container_width=True)

    st.divider()
    st.subheader("View Session Allocations")
    options = {
        f"{s.get('exam_code', '')} | Session {s['session_id']} | {s.get('exam_date')} | {s.get('start_time')}": s["session_id"]
        for s in sessions
    }
    selected_label = st.selectbox("Select Session", list(options.keys()))

    if st.button("View Allocations"):
        selected_session_id = options[selected_label]
        result = api_get(f"/allocations/session/{selected_session_id}")
        allocations = result.get("allocations", []) if isinstance(result, dict) else result or []
        st.session_state["viewed_session_allocations"] = allocations
        st.session_state["viewed_session_id"] = selected_session_id

    if st.session_state.get("viewed_session_id"):
        allocations = st.session_state.get("viewed_session_allocations", [])
        if allocations:
            st.dataframe(pd.DataFrame(allocations), use_container_width=True, hide_index=True)
            st.success(f"{len(allocations)} allocations found.")
        else:
            st.info("No allocations generated for this session yet.")

    st.divider()
    st.subheader("Download Daily Seating Plans")
    st.caption(
        "Download one Excel workbook per examination date. Each workbook has separate "
        "Morning Session and Afternoon Session sections. Downloads are snapshots; "
        "reallocation does not overwrite files already downloaded."
    )

    dates = sorted({str(s.get("exam_date")) for s in sessions if s.get("exam_date")})
    if not dates:
        st.info("No examination dates are available for export.")
    else:
        for exam_date in dates:
            date_sessions = [s for s in sessions if str(s.get("exam_date")) == exam_date]
            subject_codes = sorted({s.get("exam_code", "") for s in date_sessions if s.get("exam_code")})
            subject_text = ", ".join(subject_codes) if subject_codes else "Examination"
            button_label = f"Prepare {exam_date} - {subject_text} ({len(date_sessions)} sessions)"

            if st.button(button_label, key=f"prepare_daily_export_{exam_date}"):
                try:
                    export_response = requests.get(
                        f"{API_BASE_URL}/exports/daily-seating-plan/{exam_date}",
                        headers=get_auth_headers(),
                        timeout=120,
                    )
                    export_response.raise_for_status()
                    st.session_state[f"daily_export_bytes_{exam_date}"] = export_response.content
                    content_disposition = export_response.headers.get("Content-Disposition", "")
                    filename = "Daily_Seating_Plan_" + exam_date + ".xlsx"
                    if "filename=" in content_disposition:
                        filename = content_disposition.split("filename=", 1)[1].strip().strip('"')
                    st.session_state[f"daily_export_filename_{exam_date}"] = filename
                except Exception as error:
                    st.error(get_error_message(error))

            file_bytes = st.session_state.get(f"daily_export_bytes_{exam_date}")
            if file_bytes:
                st.download_button(
                    label=f"Download Excel - {exam_date}",
                    data=file_bytes,
                    file_name=st.session_state.get(
                        f"daily_export_filename_{exam_date}",
                        f"Daily_Seating_Plan_{exam_date}.xlsx",
                    ),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_daily_export_{exam_date}",
                )

except Exception as error:
    st.error(f"Seat Allocation error: {get_error_message(error)}")
