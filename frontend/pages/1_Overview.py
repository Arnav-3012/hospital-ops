import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

API_URL = "http://localhost:8000"

if not st.session_state.get("token"):
    st.warning("Please login from the Home page first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}
st.title("📊 Hospital Overview")

col_refresh, _ = st.columns([1,5])
with col_refresh:
    if st.button("🔄 Refresh"):
        st.rerun()

st.divider()

# ── ROW 1: Two charts side by side ──────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("🛏️ Bed Occupancy by Department")
    try:
        data = requests.get(f"{API_URL}/analytics/bed-occupancy",
            headers=headers).json()
        df = pd.DataFrame(data)

        # Summary metrics above chart
        total_beds = df["count"].sum()
        occupied = df[df["status"]=="occupied"]["count"].sum()
        available = df[df["status"]=="available"]["count"].sum()
        occ_rate = (occupied/total_beds*100) if total_beds > 0 else 0

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Beds", int(total_beds))
        with m2:
            st.metric("Occupied", int(occupied))
        with m3:
            st.metric("Occupancy Rate", f"{occ_rate:.1f}%")

        fig = px.bar(df, x="department", y="count", color="status",
            barmode="group",
            color_discrete_map={
                "occupied": "#EF4444",
                "available": "#22C55E",
                "maintenance": "#F59E0B"},
            labels={"count": "Beds", "department": "Department"})
        fig.update_layout(
            xaxis_tickangle=-45,
            height=350,
            margin=dict(t=10, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

with col2:
    st.subheader("💰 Monthly Revenue Trend")
    try:
        data = requests.get(f"{API_URL}/analytics/revenue-trend",
            headers=headers).json()
        df = pd.DataFrame(data)
        df["total_billed"] = pd.to_numeric(df["total_billed"])
        df["total_paid"] = pd.to_numeric(df["total_paid"])
        df["outstanding"] = pd.to_numeric(df["outstanding"])

        total_billed = df["total_billed"].sum()
        total_paid = df["total_paid"].sum()
        total_outstanding = df["outstanding"].sum()
        collection_rate = (total_paid/total_billed*100) if total_billed > 0 else 0

        def format_inr(amount):
            if amount >= 10000000:
                return f"₹{amount/10000000:.2f} Cr"
            elif amount >= 100000:
                return f"₹{amount/100000:.2f} L"
            elif amount >= 1000:
                return f"₹{amount/1000:.1f} K"
            else:
                return f"₹{amount:,.0f}"

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Billed", format_inr(total_billed),
                help=f"₹{total_billed:,.0f}")
        with m2:
            st.metric("Collected", format_inr(total_paid),
                help=f"₹{total_paid:,.0f}")
        with m3:
            st.metric("Collection Rate", f"{collection_rate:.1f}%")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["month"],
            y=df["total_paid"],
            name="Paid",
            marker_color="#22C55E"
        ))
        fig.add_trace(go.Bar(
            x=df["month"],
            y=df["outstanding"],
            name="Outstanding",
            marker_color="#EF4444"
        ))
        fig.update_layout(
            barmode="stack",
            height=350,
            margin=dict(t=10, b=10),
            xaxis_tickangle=-45,
            yaxis_title="Amount (₹)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}")

st.divider()

# ── ROW 2: Inventory alerts full width ──────────────────────
st.subheader("🚨 Inventory Alerts — Items Below Reorder Level")
try:
    data = requests.get(f"{API_URL}/analytics/inventory-alerts",
        headers=headers).json()
    df_inv = pd.DataFrame(data)
    if len(df_inv) > 0:
        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Items Below Reorder", len(df_inv))
        with c2:
            st.metric("Most Critical Dept",
                df_inv.groupby("department").size().idxmax())
        with c3:
            st.metric("Avg Shortage",
                f"{df_inv['shortage'].mean():.0f} units")
        with c4:
            st.metric("Total Shortage Value",
                format_inr(
                    (df_inv["shortage"] * df_inv["unit_cost"]).sum()
                ))

        # Full width table
        st.dataframe(df_inv, use_container_width=True, height=250)
        st.caption(f"⚠️ {len(df_inv)} items need restocking")
    else:
        st.success("✅ All inventory items are sufficiently stocked.")
except Exception as e:
    st.error(f"Error loading inventory data: {e}")
