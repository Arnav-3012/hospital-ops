import streamlit as st
import requests
import plotly.express as px
import pandas as pd

API_URL = "http://localhost:8000"

if not st.session_state.get("token"):
    st.warning("Please login from the Home page first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}
st.title("👨‍⚕️ Doctor Load Analysis")

col_refresh, _ = st.columns([1,5])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

st.divider()

try:
    data = requests.get(f"{API_URL}/analytics/doctor-load",
        headers=headers).json()
    df = pd.DataFrame(data)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Doctors", len(df))
    with col2:
        st.metric("Avg Appointments per Doctor",
            f"{df['total_appointments'].mean():.0f}")
    with col3:
        busiest = df.loc[df['total_appointments'].idxmax(), 'doctor_name']
        st.metric("Busiest Doctor", busiest)

    st.divider()
    st.subheader("Top 20 Doctors by Appointment Load")
    top20 = df.nlargest(20, "total_appointments")
    fig = px.bar(top20,
        x="total_appointments",
        y="doctor_name",
        orientation="h",
        color="department",
        title="Doctor Workload — Top 20",
        labels={
            "total_appointments": "Total Appointments",
            "doctor_name": "Doctor"
        })
    fig.update_layout(height=600, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Full Doctor Load Table")
    dept_filter = st.multiselect("Filter by department",
        options=df["department"].unique().tolist(),
        default=[])
    if dept_filter:
        filtered = df[df["department"].isin(dept_filter)]
    else:
        filtered = df
    st.dataframe(filtered, use_container_width=True, height=400)
    st.caption(f"Showing {len(filtered)} of {len(df)} doctors")

except Exception as e:
    st.error(f"Error loading doctor data: {e}")
