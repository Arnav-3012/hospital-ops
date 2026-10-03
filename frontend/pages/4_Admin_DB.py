import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime

API_URL = "http://localhost:8000"
UNDO_LOG = "backend/undo_log.json"

if not st.session_state.get("token"):
    st.warning("Please login from the Home page first.")
    st.stop()

if st.session_state.get("role") != "admin":
    st.error("🚫 Access Denied — Admin accounts only")
    st.markdown("This page is restricted to admin accounts.")
    st.info("Please logout and login with admin/admin123")
    st.stop()

h_read = {"Authorization": f"Bearer {st.session_state.token}"}
h_full = {
    "Authorization": f"Bearer {st.session_state.token}",
    "Content-Type": "application/json"
}

# ── Session state initialisation (ss_ prefix avoids widget key conflicts) ──
for key in [
    "ss_del_table", "ss_del_id", "ss_del_record",
    "ss_edit_record", "ss_edit_table", "ss_edit_id",
    "ss_preview_record", "ss_preview_table", "ss_preview_id",
    "ss_nl_mod_q", "ss_nl_preview_sql",
    "ss_loaded_table", "ss_loaded_data"
]:
    if key not in st.session_state:
        st.session_state[key] = None

TABLES = {
    "patients": f"{API_URL}/patients/",
    "doctors": f"{API_URL}/doctors/",
    "departments": f"{API_URL}/departments/",
    "beds": f"{API_URL}/beds/",
    "appointments": f"{API_URL}/appointments/",
    "admissions": f"{API_URL}/admissions/",
    "prescriptions": f"{API_URL}/prescriptions/",
    "billing": f"{API_URL}/billing/",
    "inventory": f"{API_URL}/inventory/"
}

ID_FIELDS = {
    "patients": "patient_id",
    "doctors": "doctor_id",
    "departments": "department_id",
    "beds": "bed_id",
    "appointments": "appointment_id",
    "admissions": "admission_id",
    "prescriptions": "prescription_id",
    "billing": "bill_id",
    "inventory": "item_id"
}

def get_patients_list():
    try:
        r = requests.get(f"{API_URL}/patients/?limit=10000",
            headers=h_read)
        data = r.json()
        return {f"{p['name']} (ID: {p['patient_id']})":
                p['patient_id'] for p in data}
    except:
        return {}

def get_doctors_list():
    try:
        r = requests.get(f"{API_URL}/doctors/?limit=1000",
            headers=h_read)
        data = r.json()
        return {f"Dr. {d['name']} — {d['specialization']} (ID: {d['doctor_id']})":
                d['doctor_id'] for d in data}
    except:
        return {}

def get_departments_list():
    try:
        r = requests.get(f"{API_URL}/departments/?limit=100",
            headers=h_read)
        data = r.json()
        return {f"{d['name']} — Floor {d['floor_number']} (ID: {d['department_id']})":
                d['department_id'] for d in data}
    except:
        return {}

def get_available_beds_list():
    try:
        r = requests.get(f"{API_URL}/beds/?limit=10000",
            headers=h_read)
        all_beds = r.json()
        available = [b for b in all_beds
                    if b['status'] == 'available']
        dept_r = requests.get(
            f"{API_URL}/departments/?limit=100",
            headers=h_read)
        dept_map = {d['department_id']: d['name']
                   for d in dept_r.json()}
        return {
            f"Bed {b['bed_id']} — {b['ward_type']} — "
            f"{dept_map.get(b['department_id'], 'Unknown')} "
            f"(ID: {b['bed_id']})": b['bed_id']
            for b in available}
    except:
        return {}

def get_active_admissions_list():
    try:
        r = requests.get(
            f"{API_URL}/admissions/search?active_only=true&limit=1000",
            headers=h_read)
        admissions = r.json()
        pat_r = requests.get(
            f"{API_URL}/patients/?limit=10000",
            headers=h_read)
        pat_map = {p['patient_id']: p['name']
                  for p in pat_r.json()}
        return {
            f"Admission {a['admission_id']} — "
            f"{pat_map.get(a['patient_id'], 'Unknown')} "
            f"(admitted: {str(a['admitted_at'])[:10]})":
            a['admission_id']
            for a in admissions}
    except:
        return {}

def get_all_admissions_list():
    try:
        r = requests.get(
            f"{API_URL}/admissions/?limit=10000",
            headers=h_read)
        admissions = r.json()
        pat_r = requests.get(
            f"{API_URL}/patients/?limit=10000",
            headers=h_read)
        pat_map = {p['patient_id']: p['name']
                  for p in pat_r.json()}
        return {
            f"Admission {a['admission_id']} — "
            f"{pat_map.get(a['patient_id'], 'Unknown')} "
            f"(ID: {a['admission_id']})":
            a['admission_id']
            for a in admissions}
    except:
        return {}

def load_log():
    if os.path.exists(UNDO_LOG):
        with open(UNDO_LOG) as f:
            return json.load(f)
    return {}

def save_log(log):
    with open(UNDO_LOG, "w") as f:
        json.dump(log, f, indent=2, default=str)

def log_action(action, resource, record_id, old_data):
    if action == "DELETE" and resource == "patients":
        try:
            appts_r = requests.get(
                f"{API_URL}/appointments/?limit=10000",
                headers=h_read)
            appts = [a for a in appts_r.json()
                     if a.get("patient_id") == record_id]
        except:
            appts = []
        try:
            adms_r = requests.get(
                f"{API_URL}/admissions/?limit=10000",
                headers=h_read)
            adms = [a for a in adms_r.json()
                    if a.get("patient_id") == record_id]
        except:
            adms = []
        try:
            bills_r = requests.get(
                f"{API_URL}/billing/?limit=10000",
                headers=h_read)
            bills = [b for b in bills_r.json()
                     if b.get("patient_id") == record_id]
        except:
            bills = []
        old_data = {
            "patient": old_data,
            "appointments": appts,
            "admissions": adms,
            "billing": bills
        }

    log = load_log()
    eid = f"{action}_{resource}_{record_id}_{datetime.now().strftime('%H%M%S')}"
    log[eid] = {
        "action": action,
        "resource": resource,
        "record_id": record_id,
        "old_data": old_data,
        "timestamp": str(datetime.now()),
        "undone": False
    }
    if len(log) > 20:
        del log[sorted(log.keys())[0]]
    save_log(log)
    return eid

def get_record(table, record_id):
    r = requests.get(f"{TABLES[table]}{record_id}", headers=h_read)
    if r.status_code == 200:
        return r.json()
    return None

st.title("🔐 Admin — Database Explorer")
st.caption(f"Authenticated as admin: {st.session_state.username}")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📊 Overview",
    "🏥 Resources",
    "🚪 Discharge",
    "🗃️ Browse",
    "➕ Add",
    "✏️ Edit",
    "🗑️ Delete",
    "🤖 NL Modify",
    "↩️ Undo Log",
    "📋 Audit Log"
])

# ── TAB 1: OVERVIEW ─────────────────────────────────────────
with tab1:
    st.subheader("Live Row Counts — All Tables")
    if st.button("🔄 Refresh Counts"):
        st.rerun()
    st.divider()
    cols = st.columns(3)
    for i, (table, url) in enumerate(TABLES.items()):
        try:
            r = requests.get(
                f"{API_URL}/{table}/count",
                headers=h_read)
            if r.status_code == 200:
                count = r.json().get("count", 0)
            else:
                r2 = requests.get(
                    f"{url}?limit=100000",
                    headers=h_read)
                data = r2.json()
                count = len(data) if isinstance(
                    data, list) else 0
            with cols[i % 3]:
                st.metric(table.capitalize(), f"{count:,}")
        except Exception as e:
            with cols[i % 3]:
                st.metric(table.capitalize(), "Error")

# ── TAB 2: RESOURCES ─────────────────────────────────────────
with tab2:
    st.subheader("🏥 Live Hospital Resources")
    st.caption("Real-time availability — use these IDs when making changes via NL Modify")

    if st.button("🔄 Refresh Resources"):
        st.rerun()

    st.divider()

    # ── AVAILABLE BEDS ──────────────────────────────────
    st.markdown("### 🛏️ Available Beds")
    st.caption("These bed IDs can be used when admitting a patient")
    try:
        beds_data = requests.get(
            f"{API_URL}/beds/?limit=10000",
            headers=h_read).json()

        available_beds = [b for b in beds_data
                         if b["status"] == "available"]
        occupied_beds = [b for b in beds_data
                        if b["status"] == "occupied"]
        maintenance_beds = [b for b in beds_data
                           if b["status"] == "maintenance"]

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.metric("Total Beds", len(beds_data))
        with b2:
            st.metric("Available",
                len(available_beds),
                delta=f"{len(available_beds)/len(beds_data)*100:.0f}%")
        with b3:
            st.metric("Occupied", len(occupied_beds))
        with b4:
            st.metric("Maintenance", len(maintenance_beds))

        if available_beds:
            df_beds = pd.DataFrame(available_beds)

            # Get department names
            depts = requests.get(
                f"{API_URL}/departments/?limit=100",
                headers=h_read).json()
            dept_map = {d["department_id"]: d["name"]
                       for d in depts}
            df_beds["department_name"] = df_beds[
                "department_id"].map(dept_map)

            # Show with useful columns
            display_cols = ["bed_id", "department_name",
                          "ward_type", "status"]
            st.dataframe(
                df_beds[display_cols],
                use_container_width=True,
                height=200,
                hide_index=True)
            st.caption(f"💡 Copy a bed_id from above to use in NL Modify: 'Admit patient X to bed Y'")
        else:
            st.warning("No available beds at this time")

    except Exception as e:
        st.error(f"Error loading beds: {e}")

    st.divider()

    # ── AVAILABLE DOCTORS ────────────────────────────────
    st.markdown("### 👨‍⚕️ Doctors & Current Load")
    st.caption("Doctor IDs and their current appointment counts")
    try:
        doctors_data = requests.get(
            f"{API_URL}/analytics/doctor-load",
            headers=h_read).json()
        df_docs = pd.DataFrame(doctors_data)

        d1, d2, d3 = st.columns(3)
        with d1:
            st.metric("Total Doctors", len(df_docs))
        with d2:
            low_load = len(df_docs[
                df_docs["total_appointments"] < 50])
            st.metric("Low Load (< 50 appts)", low_load)
        with d3:
            avg = df_docs["total_appointments"].mean()
            st.metric("Avg Appointments", f"{avg:.0f}")

        # Filter options
        dept_filter = st.selectbox(
            "Filter by department",
            ["All"] + sorted(df_docs["department"].unique().tolist()),
            key="res_dept_filter")

        if dept_filter != "All":
            df_filtered = df_docs[
                df_docs["department"] == dept_filter]
        else:
            df_filtered = df_docs

        # Get doctor IDs
        all_doctors = requests.get(
            f"{API_URL}/doctors/?limit=1000",
            headers=h_read).json()
        doc_id_map = {d["name"]: d["doctor_id"]
                     for d in all_doctors}
        df_filtered = df_filtered.copy()
        df_filtered["doctor_id"] = df_filtered[
            "doctor_name"].map(doc_id_map)

        display_cols = ["doctor_id", "doctor_name",
                       "specialization", "department",
                       "total_appointments",
                       "total_admissions"]
        st.dataframe(
            df_filtered[display_cols],
            use_container_width=True,
            height=250,
            hide_index=True)
        st.caption("💡 Copy a doctor_id to use in NL Modify: 'Book appointment with doctor X'")

    except Exception as e:
        st.error(f"Error loading doctors: {e}")

    st.divider()

    # ── ACTIVE ADMISSIONS ────────────────────────────────
    st.markdown("### 🏥 Currently Admitted Patients")
    st.caption("Patients currently in hospital — not yet discharged")
    try:
        active_adm = requests.get(
            f"{API_URL}/admissions/search?active_only=true&limit=1000",
            headers=h_read).json()

        a1, a2 = st.columns(2)
        with a1:
            st.metric("Currently Admitted", len(active_adm))
        with a2:
            total_beds = len(requests.get(
                f"{API_URL}/beds/?limit=10000",
                headers=h_read).json())
            occupancy = len(active_adm)/total_beds*100 if total_beds > 0 else 0
            st.metric("Bed Occupancy Rate", f"{occupancy:.1f}%")

        if active_adm:
            df_adm = pd.DataFrame(active_adm)

            # Get patient names
            patients_data = requests.get(
                f"{API_URL}/patients/?limit=10000",
                headers=h_read).json()
            pat_map = {p["patient_id"]: p["name"]
                      for p in patients_data}
            df_adm["patient_name"] = df_adm[
                "patient_id"].map(pat_map)

            display_cols = ["admission_id", "patient_id",
                          "patient_name", "doctor_id",
                          "bed_id", "admitted_at", "diagnosis"]
            available_cols = [c for c in display_cols
                            if c in df_adm.columns]
            st.dataframe(
                df_adm[available_cols],
                use_container_width=True,
                height=250,
                hide_index=True)
            st.caption("💡 Use admission_id to discharge: 'Update admission X discharged_at to now'")
        else:
            st.info("No active admissions currently")

    except Exception as e:
        st.error(f"Error loading admissions: {e}")

    st.divider()

    # ── LOW STOCK INVENTORY ──────────────────────────────
    st.markdown("### 📦 Low Stock Inventory")
    st.caption("Items below reorder level — needs restocking")
    try:
        low_stock = requests.get(
            f"{API_URL}/analytics/inventory-alerts",
            headers=h_read).json()

        if low_stock:
            df_stock = pd.DataFrame(low_stock)

            s1, s2, s3 = st.columns(3)
            with s1:
                st.metric("Items Below Reorder", len(df_stock))
            with s2:
                critical = len(df_stock[df_stock["quantity"] == 0])
                st.metric("Out of Stock", critical)
            with s3:
                st.metric("Most Affected Dept",
                    df_stock.groupby("department").size().idxmax())

            st.dataframe(
                df_stock,
                use_container_width=True,
                height=200,
                hide_index=True)
            st.caption("💡 Use item_id to restock: 'Update inventory item X quantity to 100'")
        else:
            st.success("✅ All inventory items sufficiently stocked")

    except Exception as e:
        st.error(f"Error loading inventory: {e}")

    st.divider()

    # ── QUICK REFERENCE ──────────────────────────────────
    st.markdown("### 📋 Quick ID Reference for NL Modify")
    st.caption("Common IDs you'll need when writing NL instructions")

    ref1, ref2 = st.columns(2)

    with ref1:
        st.markdown("**Departments:**")
        try:
            depts = requests.get(
                f"{API_URL}/departments/?limit=100",
                headers=h_read).json()
            df_dept = pd.DataFrame(depts)[
                ["department_id", "name", "floor_number"]]
            st.dataframe(df_dept, use_container_width=True,
                hide_index=True, height=200)
        except Exception as e:
            st.error(f"Error: {e}")

    with ref2:
        st.markdown("**Ward Types & Bed Counts:**")
        try:
            beds_all = requests.get(
                f"{API_URL}/beds/?limit=10000",
                headers=h_read).json()
            df_wards = pd.DataFrame(beds_all)
            ward_summary = df_wards.groupby(
                ["ward_type", "status"]
            ).size().reset_index(name="count")
            st.dataframe(ward_summary,
                use_container_width=True,
                hide_index=True, height=200)
        except Exception as e:
            st.error(f"Error: {e}")

# ── TAB 3: DISCHARGE ─────────────────────────────────────────
with tab3:
    st.subheader("🚪 Discharge Patient")
    st.caption("Select an active admission to discharge. Bed is freed automatically.")
    st.divider()

    if st.button("🔄 Refresh", key="discharge_refresh"):
        st.rerun()

    try:
        active = requests.get(
            f"{API_URL}/admissions/search?active_only=true&limit=1000",
            headers=h_read).json()
        patients_r = requests.get(
            f"{API_URL}/patients/?limit=10000",
            headers=h_read).json()
        pat_map = {p["patient_id"]: p["name"]
                  for p in patients_r}
        doctors_r = requests.get(
            f"{API_URL}/doctors/?limit=1000",
            headers=h_read).json()
        doc_map = {d["doctor_id"]: d["name"]
                  for d in doctors_r}
        beds_r = requests.get(
            f"{API_URL}/beds/?limit=10000",
            headers=h_read).json()
        bed_map = {b["bed_id"]: b["ward_type"]
                  for b in beds_r}
    except Exception as e:
        st.error(f"Error loading data: {e}")
        active = []
        pat_map = {}
        doc_map = {}
        bed_map = {}

    if not active:
        st.info("No active admissions. All patients discharged.")
    else:
        st.metric("Currently Admitted", len(active))
        st.divider()

        admission_options = {}
        for a in active:
            pat_name = pat_map.get(
                a["patient_id"],
                f"Patient {a['patient_id']}")
            doc_name = doc_map.get(
                a["doctor_id"],
                f"Doctor {a['doctor_id']}")
            ward = bed_map.get(a["bed_id"], "Unknown")
            admitted = str(
                a.get("admitted_at",""))[:10]
            label = (
                f"{pat_name} — "
                f"Bed {a['bed_id']} ({ward}) — "
                f"Dr. {doc_name} — "
                f"Admitted: {admitted} "
                f"(ID: {a['admission_id']})")
            admission_options[label] = a["admission_id"]

        selected = st.selectbox(
            "Select patient to discharge",
            list(admission_options.keys()),
            key="discharge_sel")

        if selected:
            adm_id = admission_options[selected]
            adm_detail = next(
                (a for a in active
                 if a["admission_id"] == adm_id), None)

            if adm_detail:
                st.divider()
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Patient",
                        pat_map.get(
                            adm_detail["patient_id"],
                            "Unknown"))
                with c2:
                    st.metric("Doctor",
                        f"Dr. {doc_map.get(adm_detail['doctor_id'], 'Unknown')}")
                with c3:
                    st.metric("Bed",
                        f"Bed {adm_detail['bed_id']} ({bed_map.get(adm_detail['bed_id'],'?')})")
                with c4:
                    st.metric("Admitted",
                        str(adm_detail.get(
                            "admitted_at",""))[:10])

                st.markdown(
                    f"**Diagnosis:** "
                    f"{adm_detail.get('diagnosis','Not recorded')}")
                st.divider()
                st.warning(
                    "⚠️ This will set discharge time "
                    "to NOW and free the bed.")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(
                        "✅ CONFIRM DISCHARGE",
                        type="primary",
                        use_container_width=True,
                        key="confirm_discharge"):
                        r = requests.post(
                            f"{API_URL}/admissions/{adm_id}/discharge",
                            headers=h_read)
                        if r.status_code == 200:
                            result = r.json()
                            st.success(
                                f"✅ Patient discharged! "
                                f"Bed {result['bed_id']} "
                                f"now available.")
                            st.balloons()
                            log_action(
                                "DISCHARGE",
                                "admissions",
                                adm_id,
                                adm_detail)
                            st.rerun()
                        else:
                            st.error(
                                r.json().get(
                                    "detail",
                                    "Discharge failed"))
                with col2:
                    st.info(
                        "Patient record stays in system. "
                        "Only admission is closed.")

# ── TAB 4: BROWSE ────────────────────────────────────────────
with tab4:
    st.subheader("Browse Table Data")
    sel = st.selectbox("Select table", list(TABLES.keys()), key="br_sel")
    if st.button("Load Data", type="primary", key="br_load"):
        try:
            data = requests.get(TABLES[sel], headers=h_read).json()
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, height=500)
            st.caption(f"{len(df):,} rows loaded from {sel}")
        except Exception as e:
            st.error(f"Error: {e}")

# ── TAB 5: ADD ───────────────────────────────────────────────
with tab5:
    st.subheader("➕ Add New Record")
    st.caption("Smart forms with live data — only valid options shown")

    add_t = st.selectbox(
        "Select table",
        list(TABLES.keys()),
        key="add_sel")
    st.divider()

    # ── PATIENTS ─────────────────────────────────────────
    if add_t == "patients":
        st.markdown("#### 🧑‍⚕️ Register New Patient")
        with st.form("add_patient_form"):
            c1, c2 = st.columns(2)
            with c1:
                pn = st.text_input("Full Name *")
                pd_dob = st.date_input("Date of Birth")
                pg = st.selectbox("Gender",
                    ["Male","Female","Other"])
            with c2:
                pb = st.selectbox("Blood Type",
                    ["A+","A-","B+","B-",
                     "AB+","AB-","O+","O-"])
                pc = st.text_input("Contact Number *")
                pa = st.text_area("Address", height=80)
            submitted = st.form_submit_button(
                "➕ Register Patient",
                type="primary",
                use_container_width=True)
            if submitted:
                if pn and pc:
                    payload = {
                        "name": pn,
                        "dob": str(pd_dob),
                        "gender": pg,
                        "blood_type": pb,
                        "contact": pc,
                        "address": pa}
                    r = requests.post(
                        f"{API_URL}/patients/",
                        headers=h_full,
                        json=payload)
                    if r.status_code in [200,201]:
                        new_id = r.json().get("patient_id")
                        st.success(
                            f"✅ Patient '{pn}' registered "
                            f"successfully! Patient ID: {new_id}")
                        log_action("CREATE", "patients",
                            new_id, payload)
                    else:
                        st.error(
                            f"Failed: {r.json().get('detail', r.json())}")
                else:
                    st.warning("⚠️ Name and contact are required")

    # ── DOCTORS ──────────────────────────────────────────
    elif add_t == "doctors":
        st.markdown("#### 👨‍⚕️ Add New Doctor")
        dept_options = get_departments_list()
        with st.form("add_doctor_form"):
            c1, c2 = st.columns(2)
            with c1:
                dn = st.text_input("Full Name *")
                ds = st.text_input("Specialization *")
                dc = st.text_input("Contact Number")
            with c2:
                if dept_options:
                    dd = st.selectbox(
                        "Department *",
                        list(dept_options.keys()))
                else:
                    dd = st.number_input(
                        "Department ID",
                        min_value=1, step=1)
                de = st.number_input(
                    "Years of Experience",
                    min_value=0, max_value=50, value=5)
            submitted = st.form_submit_button(
                "➕ Add Doctor",
                type="primary",
                use_container_width=True)
            if submitted:
                if dn and ds:
                    dept_id = dept_options.get(dd, dd) \
                        if dept_options else dd
                    payload = {
                        "name": dn,
                        "specialization": ds,
                        "contact": dc,
                        "years_experience": de,
                        "department_id": dept_id}
                    r = requests.post(
                        f"{API_URL}/doctors/",
                        headers=h_full,
                        json=payload)
                    if r.status_code in [200,201]:
                        new_id = r.json().get("doctor_id")
                        st.success(
                            f"✅ Dr. '{dn}' added! "
                            f"Doctor ID: {new_id}")
                        log_action("CREATE", "doctors",
                            new_id, payload)
                    else:
                        st.error(
                            f"Failed: {r.json().get('detail', r.json())}")
                else:
                    st.warning(
                        "⚠️ Name and specialization required")

    # ── DEPARTMENTS ──────────────────────────────────────
    elif add_t == "departments":
        st.markdown("#### 🏢 Add New Department")
        with st.form("add_dept_form"):
            c1, c2 = st.columns(2)
            with c1:
                dept_name = st.text_input(
                    "Department Name *")
                dept_head = st.text_input(
                    "Head Doctor Name")
            with c2:
                dept_floor = st.number_input(
                    "Floor Number",
                    min_value=1, max_value=20, value=1)
            submitted = st.form_submit_button(
                "➕ Add Department",
                type="primary",
                use_container_width=True)
            if submitted:
                if dept_name:
                    payload = {
                        "name": dept_name,
                        "head_doctor": dept_head,
                        "floor_number": dept_floor}
                    r = requests.post(
                        f"{API_URL}/departments/",
                        headers=h_full,
                        json=payload)
                    if r.status_code in [200,201]:
                        new_id = r.json().get(
                            "department_id")
                        st.success(
                            f"✅ Department '{dept_name}' "
                            f"added! ID: {new_id}")
                        log_action("CREATE", "departments",
                            new_id, payload)
                    else:
                        st.error(r.json())
                else:
                    st.warning(
                        "⚠️ Department name required")

    # ── BEDS ─────────────────────────────────────────────
    elif add_t == "beds":
        st.markdown("#### 🛏️ Add New Bed")
        dept_options_b = get_departments_list()
        with st.form("add_bed_form"):
            c1, c2 = st.columns(2)
            with c1:
                if dept_options_b:
                    bed_dept = st.selectbox(
                        "Department *",
                        list(dept_options_b.keys()),
                        key="bed_dept_sel")
                else:
                    bed_dept = st.number_input(
                        "Department ID",
                        min_value=1, step=1)
                bed_ward = st.selectbox(
                    "Ward Type",
                    ["General","ICU",
                     "Private","Semi-Private"])
            with c2:
                bed_status = st.selectbox(
                    "Initial Status",
                    ["available","maintenance"],
                    help="New beds should be available or maintenance. Occupied is set automatically when a patient is admitted.")
            submitted = st.form_submit_button(
                "➕ Add Bed",
                type="primary",
                use_container_width=True)
            if submitted:
                dept_id = dept_options_b.get(
                    bed_dept, bed_dept) \
                    if dept_options_b else bed_dept
                payload = {
                    "department_id": dept_id,
                    "ward_type": bed_ward,
                    "status": bed_status}
                r = requests.post(
                    f"{API_URL}/beds/",
                    headers=h_full,
                    json=payload)
                if r.status_code in [200,201]:
                    new_id = r.json().get("bed_id")
                    st.success(
                        f"✅ Bed added! Bed ID: {new_id}")
                    log_action("CREATE", "beds",
                        new_id, payload)
                else:
                    st.error(r.json())

    # ── APPOINTMENTS ─────────────────────────────────────
    elif add_t == "appointments":
        st.markdown("#### 📅 Book New Appointment")

        with st.spinner("Loading available doctors and patients..."):
            patient_options = get_patients_list()
            doctor_options = get_doctors_list()

        if not patient_options or not doctor_options:
            st.error("Could not load patients or doctors. Check API connection.")
        else:
            st.success(
                f"✅ {len(patient_options):,} patients and "
                f"{len(doctor_options)} doctors loaded")

            with st.form("add_appointment_form"):
                c1, c2 = st.columns(2)
                with c1:
                    pat_sel = st.selectbox(
                        "Select Patient *",
                        list(patient_options.keys()),
                        key="appt_pat_sel")
                    doc_sel = st.selectbox(
                        "Select Doctor *",
                        list(doctor_options.keys()),
                        key="appt_doc_sel")
                with c2:
                    appt_date = st.date_input(
                        "Appointment Date *")
                    appt_time = st.time_input(
                        "Appointment Time *")
                    appt_status = st.selectbox(
                        "Status",
                        ["scheduled","completed",
                         "cancelled"])
                appt_notes = st.text_area(
                    "Notes / Reason for Visit",
                    height=80)

                submitted = st.form_submit_button(
                    "📅 Book Appointment",
                    type="primary",
                    use_container_width=True)
                if submitted:
                    scheduled_dt = datetime.combine(
                        appt_date, appt_time)
                    pat_id = patient_options[pat_sel]
                    doc_id = doctor_options[doc_sel]
                    payload = {
                        "patient_id": pat_id,
                        "doctor_id": doc_id,
                        "scheduled_at":
                            scheduled_dt.isoformat(),
                        "status": appt_status,
                        "notes": appt_notes}
                    r = requests.post(
                        f"{API_URL}/appointments/",
                        headers=h_full,
                        json=payload)
                    if r.status_code in [200,201]:
                        new_id = r.json().get(
                            "appointment_id")
                        st.success(
                            f"✅ Appointment booked! "
                            f"ID: {new_id}")
                        log_action("CREATE",
                            "appointments",
                            new_id, payload)
                    else:
                        st.error(
                            f"Failed: {r.json().get('detail', r.json())}")

    # ── ADMISSIONS ───────────────────────────────────────
    elif add_t == "admissions":
        st.markdown("#### 🏥 Admit New Patient")

        with st.spinner("Loading available resources..."):
            patient_options_a = get_patients_list()
            doctor_options_a = get_doctors_list()
            available_beds = get_available_beds_list()

        if not available_beds:
            st.error(
                "❌ No beds available for admission. "
                "All beds are currently occupied or "
                "under maintenance.")
        else:
            st.success(
                f"✅ {len(available_beds)} beds available · "
                f"{len(patient_options_a):,} patients · "
                f"{len(doctor_options_a)} doctors loaded")

            with st.form("add_admission_form"):
                c1, c2 = st.columns(2)
                with c1:
                    adm_pat = st.selectbox(
                        "Select Patient *",
                        list(patient_options_a.keys()),
                        key="adm_pat_sel")
                    adm_doc = st.selectbox(
                        "Select Doctor *",
                        list(doctor_options_a.keys()),
                        key="adm_doc_sel")
                with c2:
                    adm_bed = st.selectbox(
                        "Select Available Bed *",
                        list(available_beds.keys()),
                        key="adm_bed_sel",
                        help="Only showing currently available beds")
                    adm_diag = st.text_area(
                        "Diagnosis *",
                        height=100)

                submitted = st.form_submit_button(
                    "🏥 Admit Patient",
                    type="primary",
                    use_container_width=True)
                if submitted:
                    if adm_diag:
                        pat_id = patient_options_a[adm_pat]
                        doc_id = doctor_options_a[adm_doc]
                        bed_id = available_beds[adm_bed]
                        payload = {
                            "patient_id": pat_id,
                            "doctor_id": doc_id,
                            "bed_id": bed_id,
                            "diagnosis": adm_diag}
                        r = requests.post(
                            f"{API_URL}/admissions/",
                            headers=h_full,
                            json=payload)
                        if r.status_code in [200,201]:
                            new_id = r.json().get(
                                "admission_id")
                            st.success(
                                f"✅ Patient admitted! "
                                f"Admission ID: {new_id}. "
                                f"Bed automatically marked "
                                f"as occupied.")
                            log_action("CREATE",
                                "admissions",
                                new_id, payload)
                        else:
                            st.error(
                                f"Failed: {r.json().get('detail', r.json())}")
                    else:
                        st.warning("⚠️ Diagnosis required")

    # ── PRESCRIPTIONS ────────────────────────────────────
    elif add_t == "prescriptions":
        st.markdown("#### 💊 Add Prescription")

        with st.spinner("Loading active admissions..."):
            active_adm_options = get_active_admissions_list()
            doctor_options_p = get_doctors_list()

        if not active_adm_options:
            st.warning(
                "⚠️ No active admissions found. "
                "Prescriptions can only be added to "
                "currently admitted patients.")
        else:
            st.success(
                f"✅ {len(active_adm_options)} active "
                f"admissions loaded")

            with st.form("add_prescription_form"):
                c1, c2 = st.columns(2)
                with c1:
                    presc_adm = st.selectbox(
                        "Select Active Admission *",
                        list(active_adm_options.keys()),
                        key="presc_adm_sel",
                        help="Only showing currently admitted patients")
                    presc_doc = st.selectbox(
                        "Prescribing Doctor *",
                        list(doctor_options_p.keys()),
                        key="presc_doc_sel")
                with c2:
                    presc_med = st.text_input(
                        "Medication Name *",
                        placeholder="e.g. Paracetamol")
                    presc_dosage = st.text_input(
                        "Dosage *",
                        placeholder="e.g. 500mg twice daily")
                    presc_days = st.number_input(
                        "Duration (days)",
                        min_value=1,
                        max_value=365,
                        value=7)

                submitted = st.form_submit_button(
                    "💊 Add Prescription",
                    type="primary",
                    use_container_width=True)
                if submitted:
                    if presc_med and presc_dosage:
                        adm_id = active_adm_options[
                            presc_adm]
                        doc_id = doctor_options_p[
                            presc_doc]
                        payload = {
                            "admission_id": adm_id,
                            "doctor_id": doc_id,
                            "medication": presc_med,
                            "dosage": presc_dosage,
                            "duration_days": presc_days}
                        r = requests.post(
                            f"{API_URL}/prescriptions/",
                            headers=h_full,
                            json=payload)
                        if r.status_code in [200,201]:
                            new_id = r.json().get(
                                "prescription_id")
                            st.success(
                                f"✅ Prescription for "
                                f"'{presc_med}' added! "
                                f"ID: {new_id}")
                            log_action("CREATE",
                                "prescriptions",
                                new_id, payload)
                        else:
                            st.error(
                                f"Failed: {r.json().get('detail', r.json())}")
                    else:
                        st.warning(
                            "⚠️ Medication and dosage required")

    # ── BILLING ──────────────────────────────────────────
    elif add_t == "billing":
        st.markdown("#### 💰 Add Billing Record")

        with st.spinner("Loading admissions..."):
            all_adm_options = get_all_admissions_list()
            patient_options_b = get_patients_list()

        with st.form("add_billing_form"):
            c1, c2 = st.columns(2)
            with c1:
                if patient_options_b:
                    bill_pat = st.selectbox(
                        "Select Patient *",
                        list(patient_options_b.keys()),
                        key="bill_pat_sel")
                else:
                    bill_pat = st.number_input(
                        "Patient ID",
                        min_value=1, step=1)
                if all_adm_options:
                    bill_adm = st.selectbox(
                        "Select Admission *",
                        list(all_adm_options.keys()),
                        key="bill_adm_sel")
                else:
                    bill_adm = st.number_input(
                        "Admission ID",
                        min_value=1, step=1)
            with c2:
                bill_total = st.number_input(
                    "Total Amount (₹) *",
                    min_value=0.0,
                    value=10000.0,
                    step=1000.0)
                bill_paid = st.number_input(
                    "Paid Amount (₹)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0)
                bill_status = st.selectbox(
                    "Payment Status",
                    ["pending","partial","paid"])

            submitted = st.form_submit_button(
                "💰 Add Bill",
                type="primary",
                use_container_width=True)
            if submitted:
                pat_id = patient_options_b.get(
                    bill_pat, bill_pat) \
                    if patient_options_b else bill_pat
                adm_id = all_adm_options.get(
                    bill_adm, bill_adm) \
                    if all_adm_options else bill_adm
                payload = {
                    "patient_id": pat_id,
                    "admission_id": adm_id,
                    "total_amount": bill_total,
                    "paid_amount": bill_paid,
                    "payment_status": bill_status}
                r = requests.post(
                    f"{API_URL}/billing/",
                    headers=h_full,
                    json=payload)
                if r.status_code in [200,201]:
                    new_id = r.json().get("bill_id")
                    st.success(
                        f"✅ Bill of "
                        f"₹{bill_total:,.0f} added! "
                        f"Bill ID: {new_id}")
                    log_action("CREATE", "billing",
                        new_id, payload)
                else:
                    st.error(
                        f"Failed: {r.json().get('detail', r.json())}")

    # ── INVENTORY ────────────────────────────────────────
    elif add_t == "inventory":
        st.markdown("#### 📦 Add Inventory Item")
        dept_options_i = get_departments_list()
        with st.form("add_inventory_form"):
            c1, c2 = st.columns(2)
            with c1:
                inv_name = st.text_input(
                    "Item Name *",
                    placeholder="e.g. Paracetamol 500mg")
                inv_cat = st.selectbox(
                    "Category",
                    ["Medicine","Equipment",
                     "Consumable","Lab Supply"])
                inv_qty = st.number_input(
                    "Initial Quantity",
                    min_value=0,
                    max_value=10000,
                    value=100)
            with c2:
                if dept_options_i:
                    inv_dept = st.selectbox(
                        "Department *",
                        list(dept_options_i.keys()),
                        key="inv_dept_sel")
                else:
                    inv_dept = st.number_input(
                        "Department ID",
                        min_value=1, step=1)
                inv_reorder = st.number_input(
                    "Reorder Level",
                    min_value=0,
                    max_value=1000,
                    value=10)
                inv_cost = st.number_input(
                    "Unit Cost (₹)",
                    min_value=0.0,
                    max_value=100000.0,
                    value=100.0,
                    step=10.0)

            submitted = st.form_submit_button(
                "📦 Add Item",
                type="primary",
                use_container_width=True)
            if submitted:
                if inv_name:
                    dept_id = dept_options_i.get(
                        inv_dept, inv_dept) \
                        if dept_options_i else inv_dept
                    payload = {
                        "item_name": inv_name,
                        "category": inv_cat,
                        "quantity": inv_qty,
                        "reorder_level": inv_reorder,
                        "unit_cost": inv_cost,
                        "department_id": dept_id}
                    r = requests.post(
                        f"{API_URL}/inventory/",
                        headers=h_full,
                        json=payload)
                    if r.status_code in [200,201]:
                        new_id = r.json().get("item_id")
                        st.success(
                            f"✅ '{inv_name}' added! "
                            f"Item ID: {new_id}")
                        log_action("CREATE", "inventory",
                            new_id, payload)
                    else:
                        st.error(
                            f"Failed: {r.json().get('detail', r.json())}")
                else:
                    st.warning("⚠️ Item name required")

# ── TAB 6: EDIT ──────────────────────────────────────────────
with tab6:
    st.subheader("Edit an Existing Record")
    st.caption("Load a record by ID, edit the fields, preview changes, then confirm to save to database.")
    st.divider()

    e_table = st.selectbox("Table", list(TABLES.keys()), key="ed_table")
    e_id = st.number_input(
        f"Enter {ID_FIELDS[e_table]}",
        min_value=1, step=1, key="ed_id")

    if st.button("🔍 Load Record", key="ed_load"):
        record = get_record(e_table, e_id)
        if record:
            st.session_state.ss_edit_record = record
            st.session_state.ss_edit_table = e_table
            st.session_state.ss_edit_id = e_id
            st.success(f"Record loaded. Edit fields below.")
        else:
            st.error("Record not found")

    if st.session_state.get("ss_edit_record"):
        record = st.session_state.ss_edit_record
        id_field = ID_FIELDS[st.session_state.ss_edit_table]
        st.divider()
        st.markdown("**Edit fields — leave blank to keep current value:**")
        edited = {}
        cols_edit = st.columns(2)
        fields = [(k,v) for k,v in record.items() if k != id_field]
        for i, (field, value) in enumerate(fields):
            with cols_edit[i % 2]:
                new_val = st.text_input(
                    f"{field} (current: {value})",
                    value="",
                    key=f"ef_{field}",
                    placeholder=str(value) if value else "")
                if new_val.strip():
                    edited[field] = new_val

        if edited:
            st.divider()
            st.markdown("**Preview of changes:**")
            prev_data = []
            for field, new_val in edited.items():
                prev_data.append({
                    "Field": field,
                    "Current Value": record.get(field),
                    "New Value": new_val
                })
            st.dataframe(pd.DataFrame(prev_data),
                use_container_width=True, hide_index=True)

            st.warning("⚠️ Clicking confirm will apply these changes to the live database.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ CONFIRM — Apply Changes to Database",
                             type="primary", use_container_width=True):
                    eid = log_action("UPDATE",
                        st.session_state.ss_edit_table,
                        st.session_state.ss_edit_id,
                        record)
                    r = requests.put(
                        f"{TABLES[st.session_state.ss_edit_table]}{st.session_state.ss_edit_id}",
                        headers=h_full,
                        json=edited)
                    if r.status_code == 200:
                        st.success(f"✅ Record updated in database! Log ID: {eid}")
                        st.info("You can undo this in the Undo Log tab")
                        st.session_state.ss_edit_record = None
                        st.rerun()
                    else:
                        st.error(f"Update failed: {r.json()}")
            with c2:
                if st.button("❌ Cancel", use_container_width=True, key="ed_cancel"):
                    st.session_state.ss_edit_record = None
                    st.rerun()
        else:
            st.info("Edit the fields above to see a preview of changes.")
            if st.button("❌ Cancel", use_container_width=True, key="ed_cancel2"):
                st.session_state.ss_edit_record = None
                st.rerun()

# ── TAB 7: DELETE ────────────────────────────────────────────
with tab7:
    st.subheader("Delete a Record")
    st.caption("Load a record by ID to preview it, then confirm to permanently delete from database.")
    st.divider()

    d_table = st.selectbox("Table", list(TABLES.keys()), key="del_table")
    d_id = st.number_input(
        f"Enter {ID_FIELDS[d_table]} to delete",
        min_value=1, step=1, key="del_id")

    if st.button("🔍 Preview Record Before Delete", key="del_preview"):
        record = get_record(d_table, d_id)
        if record:
            st.session_state.ss_del_record = record
            st.session_state.ss_del_table = d_table
            st.session_state.ss_del_id = d_id
        else:
            st.error("Record not found")

    if st.session_state.get("ss_del_record"):
        st.divider()
        st.markdown("**Record to be deleted:**")
        st.json(st.session_state.ss_del_record)
        st.error("⚠️ This action will permanently delete this record from the live database.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ CONFIRM DELETE — Apply to Database",
                         type="primary", use_container_width=True):
                eid = log_action("DELETE",
                    st.session_state.ss_del_table,
                    st.session_state.ss_del_id,
                    st.session_state.ss_del_record)
                r = requests.delete(
                    f"{TABLES[st.session_state.ss_del_table]}{st.session_state.ss_del_id}",
                    headers=h_read)
                if r.status_code in [200, 204]:
                    st.success(f"✅ Record deleted from database! Log ID: {eid}")
                    st.info("You can undo this in the Undo Log tab")
                    st.session_state.ss_del_record = None
                    st.rerun()
                else:
                    st.error(f"Delete failed: {r.json()}")
        with c2:
            if st.button("❌ Cancel Delete",
                         use_container_width=True, key="del_cancel"):
                st.session_state.ss_del_record = None
                st.rerun()

# ── TAB 8: NL MODIFY ────────────────────────────────────────
with tab8:
    st.subheader("🤖 Natural Language Database Modifications")
    st.markdown("""
Type what you want in plain English.
**Admin only** — executes INSERT, UPDATE, DELETE directly on database.
Every modification is logged to the audit log automatically.
""")

    st.warning("⚠️ Changes apply directly to the live database. Use carefully.")
    st.divider()

    NL_MOD_EXAMPLES = [
        "Insert a new patient named John Doe born 1990-01-01 male O+ contact 9876543210",
        "Update patient id 1 contact to 9999999999",
        "Delete appointment id 1",
        "Update bed id 5 status to available",
        "Update billing id 1 payment_status to paid",
        "Delete prescription id 1"
    ]

    st.markdown("**Example instructions:**")
    ecols = st.columns(2)
    for i, ex in enumerate(NL_MOD_EXAMPLES):
        with ecols[i % 2]:
            if st.button(ex, key=f"nlmod_ex_{i}", use_container_width=True):
                st.session_state.ss_nl_mod_q = ex

    nl_q = st.text_area(
        "Your instruction:",
        value=st.session_state.get("ss_nl_mod_q") or "",
        height=100,
        placeholder="e.g. Update patient id 5 blood type to A+")

    # ── Preview button ────────────────────────────────────
    if st.button("🔍 Preview SQL First", use_container_width=True):
        if nl_q.strip():
            with st.spinner("Generating SQL preview..."):
                try:
                    r = requests.post(
                        f"{API_URL}/query/preview",
                        headers={**h_read,
                            "Content-Type": "application/json"},
                        json={"question": nl_q})
                    if r.status_code == 200:
                        result = r.json()
                        st.session_state.ss_nl_preview_sql = \
                            result["sql"]
                        op = result["operation_type"]
                        if op == "SELECT":
                            st.success(f"✅ READ ONLY — {op}")
                        elif op == "INSERT":
                            st.info(f"➕ WILL INSERT — {op}")
                        elif op == "UPDATE":
                            st.warning(f"✏️ WILL UPDATE — {op}")
                        elif op == "DELETE":
                            st.error(f"🗑️ WILL DELETE — {op}")
                        st.markdown("**Generated SQL:**")
                        st.code(result["sql"], language="sql")
                        if result["is_modification"]:
                            st.warning(
                                "⚠️ This will modify the live "
                                "database. Review carefully "
                                "before clicking Execute.")
                        else:
                            st.info(
                                "This is a read-only query. "
                                "Safe to execute.")
                    else:
                        st.error(
                            r.json().get("detail",
                                "Preview failed"))
                except Exception as e:
                    st.error(f"Preview error: {e}")
        else:
            st.warning("Enter an instruction first")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⚡ EXECUTE — Apply to Database",
                     type="primary",
                     use_container_width=True):
            if nl_q.strip():
                with st.spinner("Executing..."):
                    try:
                        r = requests.post(
                            f"{API_URL}/query/modify",
                            headers={**h_read, "Content-Type": "application/json"},
                            json={"question": nl_q})
                        if r.status_code == 200:
                            result = r.json()
                            sql = result.get("sql", "")
                            sql_upper = sql.upper().strip()

                            # Log to undo log for potential undo
                            if any(sql_upper.startswith(op)
                                   for op in ["UPDATE", "DELETE", "INSERT"]):
                                eid = log_action(
                                    "NL_MODIFY",
                                    "database",
                                    0,
                                    {
                                        "sql": sql,
                                        "question": nl_q,
                                        "rows_affected": result.get(
                                            "rows_affected", 0),
                                        "executed_by": st.session_state.username,
                                        "note": "Use NL Modify to reverse this manually"
                                    }
                                )

                            st.success(f"✅ {result['message']}")
                            st.code(result["sql"], language="sql")
                            st.metric("Rows Affected", result["rows_affected"])
                            st.session_state.ss_nl_mod_q = ""
                            st.info("✅ Logged to Audit Log tab — click Refresh Log to see it")
                        else:
                            st.error(r.json().get("detail", "Execution failed"))
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter an instruction")
    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.ss_nl_mod_q = ""
            st.rerun()

    st.divider()
    st.caption("""
Safety rules enforced:
→ DROP, TRUNCATE, ALTER, CREATE are blocked
→ UPDATE and DELETE require a WHERE clause
→ Every execution logged to audit log with username and timestamp
→ Only admin accounts can access this endpoint
""")

# ── TAB 9: UNDO LOG ─────────────────────────────────────────
with tab9:
    st.subheader("↩️ Undo Log — Last 20 Actions")
    st.caption("Every add, edit and delete is logged here. Click Undo to restore.")
    if st.button("🔄 Refresh Log"):
        st.rerun()
    st.divider()

    log = load_log()
    active_entries = {k:v for k,v in log.items() if not v.get("undone")}

    if not active_entries:
        st.info("No actions logged yet. Actions appear here after you add, edit or delete records.")
    else:
        for eid, entry in sorted(active_entries.items(), reverse=True):
            action_emoji = {
                "CREATE": "➕",
                "UPDATE": "✏️",
                "DELETE": "🗑️"
            }.get(entry["action"], "•")

            with st.expander(
                f"{action_emoji} {entry['action']} on "
                f"{entry['resource']} "
                f"(ID: {entry['record_id']}) — "
                f"{entry['timestamp']}"
            ):
                st.markdown("**Snapshot before action:**")
                st.json(entry["old_data"])

                if entry["action"] in ["DELETE", "UPDATE"]:
                    if st.button(f"↩️ Undo this {entry['action']}",
                                 key=f"undo_{eid}",
                                 type="primary"):
                        if entry["action"] == "DELETE":
                            old = entry["old_data"]
                            resource = entry["resource"]

                            if (resource == "patients"
                                    and isinstance(old, dict)
                                    and "patient" in old):
                                # Enriched patient delete — restore in FK order
                                patient_data = old["patient"]
                                appointments = old.get("appointments", [])
                                admissions   = old.get("admissions", [])
                                billing      = old.get("billing", [])

                                # 1. Restore patient
                                pat_payload = {
                                    k: v for k, v in patient_data.items()
                                    if k != ID_FIELDS["patients"]
                                }
                                r = requests.post(
                                    TABLES["patients"],
                                    headers=h_full,
                                    json=pat_payload)
                                if r.status_code not in [200, 201]:
                                    st.error(
                                        f"Patient restore failed: {r.json()}")
                                else:
                                    new_pid = r.json().get("patient_id")
                                    errors = []

                                    # 2. Restore appointments
                                    for appt in appointments:
                                        appt_payload = {
                                            k: v for k, v in appt.items()
                                            if k != ID_FIELDS["appointments"]
                                        }
                                        appt_payload["patient_id"] = new_pid
                                        rr = requests.post(
                                            TABLES["appointments"],
                                            headers=h_full,
                                            json=appt_payload)
                                        if rr.status_code not in [200, 201]:
                                            errors.append(
                                                f"Appointment failed: "
                                                f"{rr.json()}")

                                    # 3. Restore admissions
                                    for adm in admissions:
                                        adm_payload = {
                                            k: v for k, v in adm.items()
                                            if k != ID_FIELDS["admissions"]
                                        }
                                        adm_payload["patient_id"] = new_pid
                                        rr = requests.post(
                                            TABLES["admissions"],
                                            headers=h_full,
                                            json=adm_payload)
                                        if rr.status_code not in [200, 201]:
                                            errors.append(
                                                f"Admission failed: "
                                                f"{rr.json()}")

                                    # 4. Restore billing
                                    for bill in billing:
                                        bill_payload = {
                                            k: v for k, v in bill.items()
                                            if k != ID_FIELDS["billing"]
                                        }
                                        bill_payload["patient_id"] = new_pid
                                        rr = requests.post(
                                            TABLES["billing"],
                                            headers=h_full,
                                            json=bill_payload)
                                        if rr.status_code not in [200, 201]:
                                            errors.append(
                                                f"Billing failed: "
                                                f"{rr.json()}")

                                    log[eid]["undone"] = True
                                    save_log(log)
                                    if errors:
                                        st.warning(
                                            f"Patient restored "
                                            f"(new ID: {new_pid}) but "
                                            f"some related records "
                                            f"failed:\n"
                                            + "\n".join(errors))
                                    else:
                                        st.success(
                                            f"✅ Patient restored "
                                            f"(new ID: {new_pid}) with "
                                            f"{len(appointments)} "
                                            f"appointment(s), "
                                            f"{len(admissions)} "
                                            f"admission(s), "
                                            f"{len(billing)} "
                                            f"billing record(s).")
                                    st.rerun()
                            else:
                                # Standard single-record restore
                                id_field = ID_FIELDS[resource]
                                payload = {k: v for k, v in old.items()
                                           if k != id_field}
                                r = requests.post(
                                    TABLES[resource],
                                    headers=h_full,
                                    json=payload)
                                if r.status_code in [200, 201]:
                                    log[eid]["undone"] = True
                                    save_log(log)
                                    st.success(
                                        "✅ Record restored to database!")
                                    st.rerun()
                                else:
                                    st.error(
                                        f"Restore failed: {r.json()}")
                        elif entry["action"] == "UPDATE":
                            r = requests.put(
                                f"{TABLES[entry['resource']]}{entry['record_id']}",
                                headers=h_full,
                                json=entry["old_data"])
                            if r.status_code == 200:
                                log[eid]["undone"] = True
                                save_log(log)
                                st.success("✅ Record restored to previous state!")
                                st.rerun()
                            else:
                                st.error(f"Undo failed: {r.json()}")
                else:
                    st.caption("CREATE actions cannot be undone via log — use Delete tab to remove.")

# ── TAB 10: AUDIT LOG ────────────────────────────────────────
with tab10:
    st.subheader("📋 Audit Log — All Database Changes")
    st.caption("Every INSERT, UPDATE, DELETE recorded automatically")

    col1, col2, col3 = st.columns(3)
    with col1:
        filter_table = st.selectbox(
            "Filter by table",
            ["all"] + list(TABLES.keys()),
            key="audit_table")
    with col2:
        filter_op = st.selectbox(
            "Filter by operation",
            ["all", "INSERT", "UPDATE", "DELETE"],
            key="audit_op")
    with col3:
        filter_user = st.text_input("Filter by user", key="audit_user")

    auto_load = True
    col_load, col_filter = st.columns([1, 3])
    with col_load:
        if st.button("🔄 Refresh Log", type="primary"):
            st.rerun()

    if auto_load:
        params = {"limit": 200}
        if filter_table != "all":
            params["table_name"] = filter_table
        if filter_op != "all":
            params["operation"] = filter_op
        if filter_user:
            params["changed_by"] = filter_user

        try:
            r = requests.get(
                f"{API_URL}/audit-log/",
                headers=h_read,
                params=params)
            if r.status_code == 200:
                data = r.json()
                if data:
                    df = pd.DataFrame(data)
                    cols_to_show = [
                        "log_id", "table_name", "operation",
                        "record_id", "changed_by", "changed_at"]
                    st.dataframe(
                        df[cols_to_show],
                        use_container_width=True,
                        height=400)
                    st.caption(f"{len(df)} entries found")

                    if st.checkbox("Show full details with old/new values"):
                        st.dataframe(df, use_container_width=True)
                else:
                    st.info("No audit entries found for these filters")
            else:
                st.error(f"Error: {r.json()}")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.subheader("📊 Audit Summary")
    if st.button("Load Summary"):
        try:
            r = requests.get(f"{API_URL}/audit-log/summary", headers=h_read)
            if r.status_code == 200:
                summary_data = r.json()
                if summary_data:
                    import plotly.express as px
                    df_s = pd.DataFrame(summary_data)
                    fig = px.bar(
                        df_s,
                        x="table",
                        y="count",
                        color="operation",
                        barmode="group",
                        title="Operations by Table",
                        color_discrete_map={
                            "INSERT": "#22C55E",
                            "UPDATE": "#F59E0B",
                            "DELETE": "#EF4444",
                        })
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error: {e}")
