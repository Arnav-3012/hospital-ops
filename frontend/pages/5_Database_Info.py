import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000"

if not st.session_state.get("token"):
    st.warning("Please login from the Home page first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("🗄️ Database Reference")
st.caption("Complete schema documentation and design reference")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Schema",
    "🔗 Relationships",
    "📐 Design Decisions",
    "📊 Live Stats"
])

# ── TAB 1: SCHEMA ────────────────────────────────────────────
with tab1:
    st.subheader("Database Schema — 9 Tables")
    st.caption("PostgreSQL 16 · 3NF Normalised · ACID Compliant")
    st.divider()

    tables = {
        "patients": {
            "description": "Master table for all hospital patients",
            "columns": [
                {"column": "patient_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "name", "type": "VARCHAR(100)", "constraint": "NOT NULL"},
                {"column": "dob", "type": "DATE", "constraint": ""},
                {"column": "gender", "type": "VARCHAR(10)", "constraint": ""},
                {"column": "blood_type", "type": "VARCHAR(5)", "constraint": ""},
                {"column": "contact", "type": "VARCHAR(20)", "constraint": ""},
                {"column": "address", "type": "TEXT", "constraint": ""},
            ]
        },
        "doctors": {
            "description": "Hospital doctors linked to departments",
            "columns": [
                {"column": "doctor_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "name", "type": "VARCHAR(100)", "constraint": "NOT NULL"},
                {"column": "department_id", "type": "INTEGER", "constraint": "FK → departments"},
                {"column": "specialization", "type": "VARCHAR(100)", "constraint": ""},
                {"column": "contact", "type": "VARCHAR(20)", "constraint": ""},
                {"column": "years_experience", "type": "INTEGER", "constraint": ""},
            ]
        },
        "departments": {
            "description": "Hospital departments and their floor locations",
            "columns": [
                {"column": "department_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "name", "type": "VARCHAR(100)", "constraint": "NOT NULL"},
                {"column": "head_doctor", "type": "VARCHAR(100)", "constraint": ""},
                {"column": "floor_number", "type": "INTEGER", "constraint": ""},
            ]
        },
        "beds": {
            "description": "Individual beds with availability status",
            "columns": [
                {"column": "bed_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "department_id", "type": "INTEGER", "constraint": "FK → departments"},
                {"column": "ward_type", "type": "VARCHAR(50)", "constraint": "General/ICU/Private"},
                {"column": "status", "type": "VARCHAR(20)", "constraint": "available/occupied/maintenance"},
            ]
        },
        "appointments": {
            "description": "Outpatient appointments between patients and doctors",
            "columns": [
                {"column": "appointment_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "patient_id", "type": "INTEGER", "constraint": "FK → patients"},
                {"column": "doctor_id", "type": "INTEGER", "constraint": "FK → doctors"},
                {"column": "scheduled_at", "type": "TIMESTAMP", "constraint": "NOT NULL"},
                {"column": "status", "type": "VARCHAR(20)", "constraint": "scheduled/completed/cancelled"},
                {"column": "notes", "type": "TEXT", "constraint": ""},
            ]
        },
        "admissions": {
            "description": "Inpatient admissions — central hub table linking patient, doctor and bed",
            "columns": [
                {"column": "admission_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "patient_id", "type": "INTEGER", "constraint": "FK → patients"},
                {"column": "doctor_id", "type": "INTEGER", "constraint": "FK → doctors"},
                {"column": "bed_id", "type": "INTEGER", "constraint": "FK → beds"},
                {"column": "admitted_at", "type": "TIMESTAMP", "constraint": "DEFAULT NOW()"},
                {"column": "discharged_at", "type": "TIMESTAMP", "constraint": "NULL = still admitted"},
                {"column": "diagnosis", "type": "TEXT", "constraint": ""},
            ]
        },
        "prescriptions": {
            "description": "Medications prescribed during an admission",
            "columns": [
                {"column": "prescription_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "admission_id", "type": "INTEGER", "constraint": "FK → admissions"},
                {"column": "doctor_id", "type": "INTEGER", "constraint": "FK → doctors"},
                {"column": "medication", "type": "VARCHAR(200)", "constraint": "NOT NULL"},
                {"column": "dosage", "type": "VARCHAR(100)", "constraint": ""},
                {"column": "duration_days", "type": "INTEGER", "constraint": ""},
                {"column": "prescribed_at", "type": "TIMESTAMP", "constraint": "DEFAULT NOW()"},
            ]
        },
        "billing": {
            "description": "Financial records linked to admissions",
            "columns": [
                {"column": "bill_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "patient_id", "type": "INTEGER", "constraint": "FK → patients"},
                {"column": "admission_id", "type": "INTEGER", "constraint": "FK → admissions"},
                {"column": "total_amount", "type": "NUMERIC(10,2)", "constraint": ""},
                {"column": "paid_amount", "type": "NUMERIC(10,2)", "constraint": "DEFAULT 0"},
                {"column": "payment_status", "type": "VARCHAR(20)", "constraint": "pending/partial/paid"},
                {"column": "billed_at", "type": "TIMESTAMP", "constraint": "DEFAULT NOW()"},
            ]
        },
        "inventory": {
            "description": "Medical supplies and medicines per department",
            "columns": [
                {"column": "item_id", "type": "SERIAL", "constraint": "PRIMARY KEY"},
                {"column": "department_id", "type": "INTEGER", "constraint": "FK → departments"},
                {"column": "item_name", "type": "VARCHAR(200)", "constraint": "NOT NULL"},
                {"column": "category", "type": "VARCHAR(100)", "constraint": ""},
                {"column": "quantity", "type": "INTEGER", "constraint": "DEFAULT 0"},
                {"column": "reorder_level", "type": "INTEGER", "constraint": "DEFAULT 10"},
                {"column": "unit_cost", "type": "NUMERIC(10,2)", "constraint": ""},
            ]
        }
    }

    for table_name, info in tables.items():
        with st.expander(f"📋 {table_name.upper()} — {info['description']}"):
            df = pd.DataFrame(info["columns"])
            df.columns = ["Column", "Type", "Constraint"]
            st.dataframe(df, use_container_width=True, hide_index=True)

# ── TAB 2: RELATIONSHIPS ─────────────────────────────────────
with tab2:
    st.subheader("Table Relationships — Foreign Keys")
    st.divider()

    st.markdown("""
    ### Entity Relationship Overview

    The schema is organized around **admissions** as the central hub table.
    Every clinical and financial record traces back to an admission episode.
    """)

    relationships = [
        {"From Table": "doctors", "FK Column": "department_id",
         "To Table": "departments", "Relationship": "Many doctors → One department"},
        {"From Table": "beds", "FK Column": "department_id",
         "To Table": "departments", "Relationship": "Many beds → One department"},
        {"From Table": "appointments", "FK Column": "patient_id",
         "To Table": "patients", "Relationship": "Many appointments → One patient"},
        {"From Table": "appointments", "FK Column": "doctor_id",
         "To Table": "doctors", "Relationship": "Many appointments → One doctor"},
        {"From Table": "admissions", "FK Column": "patient_id",
         "To Table": "patients", "Relationship": "Many admissions → One patient"},
        {"From Table": "admissions", "FK Column": "doctor_id",
         "To Table": "doctors", "Relationship": "Many admissions → One doctor"},
        {"From Table": "admissions", "FK Column": "bed_id",
         "To Table": "beds", "Relationship": "One admission → One bed"},
        {"From Table": "prescriptions", "FK Column": "admission_id",
         "To Table": "admissions", "Relationship": "Many prescriptions → One admission"},
        {"From Table": "prescriptions", "FK Column": "doctor_id",
         "To Table": "doctors", "Relationship": "Many prescriptions → One doctor"},
        {"From Table": "billing", "FK Column": "patient_id",
         "To Table": "patients", "Relationship": "Many bills → One patient"},
        {"From Table": "billing", "FK Column": "admission_id",
         "To Table": "admissions", "Relationship": "One bill → One admission"},
        {"From Table": "inventory", "FK Column": "department_id",
         "To Table": "departments", "Relationship": "Many items → One department"},
    ]

    df_rel = pd.DataFrame(relationships)
    st.dataframe(df_rel, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("FK Dependency Chain")
    st.code("""
departments
    ├── doctors (department_id)
    │     ├── appointments (doctor_id)
    │     ├── admissions (doctor_id)
    │     └── prescriptions (doctor_id)
    └── beds (department_id)
          └── admissions (bed_id)

patients
    ├── appointments (patient_id)
    ├── admissions (patient_id)
    └── billing (patient_id)

admissions (central hub)
    ├── prescriptions (admission_id)
    └── billing (admission_id)

departments
    └── inventory (department_id)
    """, language="text")

    st.caption("""
    Seed insertion order must respect this chain:
    departments → doctors + patients → beds →
    appointments → admissions → prescriptions + billing → inventory
    """)

# ── TAB 3: DESIGN DECISIONS ──────────────────────────────────
with tab3:
    st.subheader("Design Decisions & Justification")
    st.divider()

    decisions = [
        {
            "Decision": "PostgreSQL over MySQL or MongoDB",
            "Justification": "Hospital operations are transactional. ACID compliance is non-negotiable. Admitting a patient requires atomically inserting an admission AND updating bed status — partial failure must be impossible. PostgreSQL provides the strongest ACID guarantees of any open-source RDBMS.",
            "Alternative considered": "MongoDB — rejected because document model cannot enforce referential integrity between collections"
        },
        {
            "Decision": "3NF Normalisation",
            "Justification": "Every non-key attribute depends on the whole primary key and nothing but the primary key. No data redundancy — department name exists only in the departments table, not repeated in doctors or beds. Updates propagate correctly.",
            "Alternative considered": "Denormalised schema — rejected because billing amounts and doctor names would become inconsistent"
        },
        {
            "Decision": "Admissions as central hub table",
            "Justification": "In real hospital workflow, prescriptions and bills only exist in the context of an admission episode. Hanging both off admission_id mirrors reality and enforces the business rule at the database level via FK constraints.",
            "Alternative considered": "Linking prescriptions directly to patients — rejected because a patient can be admitted multiple times"
        },
        {
            "Decision": "Separate beds table (not a column on admissions)",
            "Justification": "A bed has its own lifecycle — available, occupied, under maintenance — independent of any patient. A bed can exist with no current admission. Modelling it as a separate entity with status allows proper resource management.",
            "Alternative considered": "bed_number column on admissions — rejected because it cannot track bed availability when unoccupied"
        },
        {
            "Decision": "Read-only DB user for NL-to-SQL",
            "Justification": "The AI layer accepts arbitrary natural language input. Even with validation, defence-in-depth requires that the database user executing AI-generated queries cannot perform writes. hospital_readonly has SELECT-only privileges.",
            "Alternative considered": "Input validation only — rejected as single point of failure"
        },
        {
            "Decision": "Indexes on all FK columns",
            "Justification": "JOIN operations between large tables (patients→admissions→prescriptions) require index scans not sequential scans. 14 indexes created across all FK columns reduce JOIN cost from O(n) to O(log n).",
            "Alternative considered": "No indexes — rejected because analytics queries on 25k+ rows were too slow"
        },
        {
            "Decision": "JWT with role-based access control",
            "Justification": "Stateless authentication scales horizontally. Role field in JWT payload allows endpoint-level access control without database lookup on every request. Admin role required for all write operations.",
            "Alternative considered": "Session-based auth — rejected because it requires server-side state"
        },
        {
            "Decision": "OLTP design (no separate OLAP layer)",
            "Justification": "At 25,000 rows, indexed PostgreSQL queries handle dashboard aggregations adequately. A separate data warehouse (DuckDB, Redshift) would add operational complexity without measurable performance benefit at this scale.",
            "Alternative considered": "DuckDB for analytics — would be justified at 10M+ rows"
        },
    ]

    for d in decisions:
        with st.expander(f"💡 {d['Decision']}"):
            st.markdown(f"**Justification:** {d['Justification']}")
            st.caption(f"Alternative considered: {d['Alternative considered']}")

# ── TAB 4: LIVE STATS ────────────────────────────────────────
with tab4:
    st.subheader("Live Database Statistics")
    st.caption("Real-time counts from the database")
    if st.button("🔄 Refresh Stats"):
        st.rerun()
    st.divider()

    TABLES_LIST = [
        "patients", "doctors", "departments", "beds",
        "appointments", "admissions", "prescriptions",
        "billing", "inventory"
    ]

    counts = []
    errors = []

    for table in TABLES_LIST:
        try:
            # Try count endpoint first
            r = requests.get(
                f"{API_URL}/{table}/count",
                headers=headers,
                timeout=5)
            if r.status_code == 200:
                count = r.json().get("count", 0)
            else:
                # Fallback — fetch all with high limit and count
                r2 = requests.get(
                    f"{API_URL}/{table}/?limit=10000",
                    headers=headers,
                    timeout=10)
                if r2.status_code == 200:
                    data = r2.json()
                    count = len(data) if isinstance(data, list) else 0
                else:
                    count = 0
                    errors.append(table)
            counts.append({"Table": table, "Row Count": count})
        except Exception as e:
            counts.append({"Table": table, "Row Count": 0})
            errors.append(f"{table}: {str(e)}")

    if counts:
        df_counts = pd.DataFrame(counts)
        total_rows = df_counts["Row Count"].sum()

        # Top summary metric
        st.metric("Total Rows Across All Tables", f"{total_rows:,}")
        st.divider()

        col1, col2 = st.columns([1, 2])

        with col1:
            st.markdown("**Row counts per table:**")
            st.dataframe(
                df_counts,
                use_container_width=True,
                hide_index=True,
                height=350)

        with col2:
            fig = px.bar(
                df_counts,
                x="Table",
                y="Row Count",
                title="Database Row Counts by Table",
                color="Row Count",
                color_continuous_scale="Blues",
                text="Row Count")
            fig.update_traces(texttemplate='%{text:,}',
                textposition='outside')
            fig.update_layout(
                height=400,
                xaxis_tickangle=-30,
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        if errors:
            st.caption(f"Note: Some endpoints had issues: {errors}")

    st.divider()
    st.subheader("Index Information")
    st.markdown("**14 indexes created on all foreign key columns:**")

    indexes = [
        {"Table": "doctors", "Index Column": "department_id", "Type": "B-tree"},
        {"Table": "beds", "Index Column": "department_id", "Type": "B-tree"},
        {"Table": "appointments", "Index Column": "patient_id", "Type": "B-tree"},
        {"Table": "appointments", "Index Column": "doctor_id", "Type": "B-tree"},
        {"Table": "admissions", "Index Column": "patient_id", "Type": "B-tree"},
        {"Table": "admissions", "Index Column": "doctor_id", "Type": "B-tree"},
        {"Table": "admissions", "Index Column": "bed_id", "Type": "B-tree"},
        {"Table": "prescriptions", "Index Column": "admission_id", "Type": "B-tree"},
        {"Table": "prescriptions", "Index Column": "doctor_id", "Type": "B-tree"},
        {"Table": "billing", "Index Column": "patient_id", "Type": "B-tree"},
        {"Table": "billing", "Index Column": "admission_id", "Type": "B-tree"},
        {"Table": "inventory", "Index Column": "department_id", "Type": "B-tree"},
    ]
    st.dataframe(
        pd.DataFrame(indexes),
        use_container_width=True,
        hide_index=True)
    st.caption(
        "B-tree indexes reduce JOIN cost from O(n) sequential scan "
        "to O(log n) index scan")
