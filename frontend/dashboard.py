import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Hospital Operations Intelligence System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

for key in ["token", "username", "role"]:
    if key not in st.session_state:
        st.session_state[key] = None

def login(username, password):
    r = requests.post(f"{API_URL}/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code == 200:
        d = r.json()
        return d["access_token"], d["role"], username
    return None, None, None

def register(username, password, role, setup_key=None):
    h = {"Content-Type": "application/json"}
    if setup_key:
        h["X-Setup-Key"] = setup_key
    return requests.post(f"{API_URL}/auth/register",
        json={"username": username, "password": password, "role": role},
        headers=h)

if not st.session_state.token:
    st.title("🏥 Hospital Operations Intelligence System")
    st.caption("NMIMS  DS Project — Semester VIII")
    st.divider()
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        tab1, tab2 = st.tabs(["🔑 Login", "📝 Register"])
        with tab1:
            st.markdown("### Welcome back")
            lu = st.text_input("Username", key="lu")
            lp = st.text_input("Password", type="password", key="lp")
            st.caption("Default accounts: admin/admin123 · demo/demo123")
            if st.button("Login", use_container_width=True, type="primary"):
                token, role, uname = login(lu, lp)
                if token:
                    st.session_state.token = token
                    st.session_state.role = role
                    st.session_state.username = uname
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        with tab2:
            st.markdown("### Create account")
            ru = st.text_input("Username", key="ru")
            rp = st.text_input("Password", type="password", key="rp")
            rp2 = st.text_input("Confirm Password", type="password", key="rp2")
            rrole = st.selectbox("Account type", ["user", "admin"],
                help="Admin accounts require authorization from existing admin")
            if rrole == "admin":
                st.divider()
                st.info("🔑 Admin accounts require the setup key from your system administrator.")
                setup_key_input = st.text_input(
                    "Setup Key",
                    type="password",
                    key="setup_key_input",
                    placeholder="Enter setup key"
                )
                st.caption("Contact your system administrator for the setup key.")
            else:
                setup_key_input = None
            if st.button("Create Account", use_container_width=True, type="primary"):
                if not ru or not rp:
                    st.error("Username and password required")
                elif rp != rp2:
                    st.error("Passwords do not match")
                elif len(rp) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    resp = register(ru, rp, rrole,
                        setup_key=setup_key_input if rrole == "admin" else None)
                    if resp.status_code in [200, 201]:
                        st.success(f"Account created as {rrole}! Please login.")
                    else:
                        st.error(resp.json().get("detail", "Registration failed"))
else:
    st.sidebar.title("🏥 Hospital Ops")
    st.sidebar.divider()
    if st.session_state.role == "admin":
        st.sidebar.success(f"👑 Admin\n{st.session_state.username}")
    else:
        st.sidebar.info(f"👤 User\n{st.session_state.username}")
    st.sidebar.divider()
    if st.sidebar.button("Logout", use_container_width=True):
        for k in ["token", "username", "role"]:
            st.session_state[k] = None
        st.rerun()

    st.title("🏥 Hospital Operations Intelligence System")
    st.caption("NMIMS MBATech DS Project — Semester IV")
    st.divider()

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    col1, col2, col3, col4 = st.columns(4)
    try:
        patients   = requests.get(f"{API_URL}/patients/?limit=10000", headers=headers).json()
        doctors    = requests.get(f"{API_URL}/doctors/?limit=10000", headers=headers).json()
        beds       = requests.get(f"{API_URL}/beds/?limit=10000", headers=headers).json()
        admissions = requests.get(f"{API_URL}/admissions/?limit=10000", headers=headers).json()
        with col1:
            st.metric("Total Patients", f"{len(patients):,}")
        with col2:
            st.metric("Total Doctors", len(doctors))
        with col3:
            occ = len([b for b in beds if b["status"] == "occupied"])
            st.metric("Occupied Beds", f"{occ}/{len(beds)}")
        with col4:
            active = len([a for a in admissions if not a.get("discharged_at")])
            st.metric("Active Admissions", active)
    except Exception as e:
        st.error(f"API not reachable. Is the server running? Error: {e}")

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.info("📊 **Overview** — Bed occupancy, revenue trends, inventory alerts")
        st.info("👨‍⚕️ **Doctors** — Workload analysis and KPI cards")
    with c2:
        st.info("🤖 **NL Query** — Ask questions in plain English")
        if st.session_state.role == "admin":
            st.success("🔐 **Admin DB** — Full database access granted")
        else:
            st.warning("🔐 **Admin DB** — Admin accounts only")
