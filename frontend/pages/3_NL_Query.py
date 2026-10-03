import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_URL = "http://localhost:8000"

if not st.session_state.get("token"):
    st.warning("Please login from the Home page first.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state.token}"}

st.title("🤖 Natural Language Query")
st.markdown("Ask any question about the hospital data in plain English. The AI generates the SQL and runs it live.")
st.divider()

# Initialize query history
if "nl_history" not in st.session_state:
    st.session_state.nl_history = []

EXAMPLES = [
    "How many patients are there in total?",
    "Which doctors have more than 100 appointments?",
    "Show all patients with unpaid bills above 50000",
    "Which department has the most occupied beds?",
    "What are the top 5 most prescribed medications?",
    "Show patients admitted in 2024 with their diagnosis",
    "Which blood type is most common among patients?",
    "List doctors in Cardiology with their years of experience",
    "How many beds are available in each department?",
    "Show the top 10 highest bills"
]

st.markdown("**Click an example query or type your own below:**")
cols = st.columns(2)
for i, q in enumerate(EXAMPLES):
    with cols[i % 2]:
        if st.button(q, key=f"ex_{i}", use_container_width=True):
            st.session_state.nl_question = q

st.divider()
question = st.text_area(
    "Your question:",
    value=st.session_state.get("nl_question", ""),
    height=100,
    placeholder="e.g. How many patients were admitted in January 2024?"
)

if st.button("🔍 Generate SQL & Run Query",
             type="primary", use_container_width=True):
    if question.strip():
        with st.spinner("AI is generating SQL..."):
            try:
                response = requests.post(
                    f"{API_URL}/query/natural",
                    headers={**headers,
                        "Content-Type":"application/json"},
                    json={"question": question})
                if response.status_code == 200:
                    result = response.json()

                    # Save to history
                    history_entry = {
                        "question": question,
                        "sql": result["sql"],
                        "columns": result["columns"],
                        "rows": result["rows"],
                        "row_count": result["row_count"],
                        "timestamp": datetime.now().strftime(
                            "%H:%M:%S")
                    }
                    st.session_state.nl_history.insert(
                        0, history_entry)
                    # Keep only last 10
                    st.session_state.nl_history = \
                        st.session_state.nl_history[:10]

                    # Show results
                    st.divider()
                    c1, c2 = st.columns([1,1])
                    with c1:
                        st.markdown("**Generated SQL:**")
                        st.code(result["sql"],
                            language="sql")
                        st.caption(
                            f"Model: LLaMA 3.1 via Groq API")
                    with c2:
                        st.markdown(
                            f"**Results — "
                            f"{result['row_count']} rows:**")
                        if result["rows"]:
                            df = pd.DataFrame(
                                result["rows"],
                                columns=result["columns"])
                            st.dataframe(
                                df,
                                use_container_width=True,
                                height=300)
                        else:
                            st.info(
                                "Query executed — "
                                "no rows returned")
                else:
                    st.error(
                        response.json().get(
                            "detail","Error"))
            except Exception as e:
                st.error(f"Connection error: {e}")
    else:
        st.warning("Please enter a question first")

# Query History section
if st.session_state.nl_history:
    st.divider()
    st.subheader("📋 Query History")
    st.caption(
        "Last 10 queries this session — "
        "click any to rerun")

    for i, entry in enumerate(
            st.session_state.nl_history):
        with st.expander(
            f"[{entry['timestamp']}] "
            f"{entry['question'][:60]}... "
            f"({entry['row_count']} rows)",
            expanded=(i==0)):

            c1, c2 = st.columns([1,1])
            with c1:
                st.code(entry["sql"], language="sql")
            with c2:
                if entry["rows"]:
                    df = pd.DataFrame(
                        entry["rows"],
                        columns=entry["columns"])
                    st.dataframe(
                        df,
                        use_container_width=True,
                        height=200)
                else:
                    st.info("No rows returned")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(
                    "🔄 Rerun this query",
                    key=f"rerun_{i}",
                    use_container_width=True):
                    st.session_state.nl_question = \
                        entry["question"]
                    st.rerun()
            with col2:
                if st.button(
                    "📋 Copy question",
                    key=f"copy_{i}",
                    use_container_width=True):
                    st.session_state.nl_question = \
                        entry["question"]
                    st.info("Question loaded into box above")

    if st.button("🗑️ Clear History",
                 use_container_width=False):
        st.session_state.nl_history = []
        st.rerun()
