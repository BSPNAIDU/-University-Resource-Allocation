import streamlit as st
from styles import load_css
import pandas as pd
import plotly.express as px
from api_client import api_get, get_error_message

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")

load_css()
st.title("📊 Optimization Analytics")

try:
    exams = api_get("/examinations/")

    if not exams:
        st.info("No examinations available for algorithm comparison.")
    else:
        options = {
            f'{e.get("exam_code")} - {e.get("subject_name")} (ID: {e["id"]})': e
            for e in exams
        }

        selected = st.selectbox("Select Examination", list(options.keys()))
        exam = options[selected]

        if st.button("Compare Optimization Algorithms", type="primary"):
            try:
                result = api_get(
                    f'/optimization/compare/{exam["id"]}'
                )
                st.session_state["comparison_result"] = result
            except Exception as e:
                st.error(get_error_message(e))

        result = st.session_state.get("comparison_result")

        if result:
            st.subheader("Comparison Results")
            st.json(result)

            def find_algorithm_rows(value):
                if isinstance(value, list):
                    if value and all(isinstance(x, dict) for x in value):
                        return value
                    for item in value:
                        found = find_algorithm_rows(item)
                        if found:
                            return found

                if isinstance(value, dict):
                    for key, item in value.items():
                        if isinstance(item, list):
                            found = find_algorithm_rows(item)
                            if found:
                                return found

                return None

            rows = find_algorithm_rows(result)

            if rows:
                df = pd.DataFrame(rows)
                st.subheader("Algorithm Data")
                st.dataframe(df, use_container_width=True, hide_index=True)

                numeric_columns = df.select_dtypes(
                    include="number"
                ).columns.tolist()

                if numeric_columns:
                    metric = st.selectbox(
                        "Select metric for comparison",
                        numeric_columns
                    )

                    name_column = next(
                        (
                            col for col in df.columns
                            if col.lower() in [
                                "algorithm", "algorithm_name", "name"
                            ]
                        ),
                        None
                    )

                    if name_column:
                        fig = px.bar(
                            df,
                            x=name_column,
                            y=metric,
                            title=f"Algorithm Comparison - {metric}"
                        )
                        st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "Comparison is informational and does not modify database allocations."
            )

except Exception as e:
    st.error(get_error_message(e))
