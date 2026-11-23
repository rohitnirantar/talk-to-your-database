"""
frontend.py - the web page (Streamlit)

Run it:  streamlit run frontend.py
It uses the same ask() function as the terminal version in main.py.
"""

import pandas as pd
import streamlit as st

import make_data
from llm import MODEL, PROVIDER, check_setup
from main import ask
from schema import DB_PATH, SCHEMA_TEXT

MAX_QUESTIONS_PER_SESSION = 15    # a public page needs a limit, so nobody can run up a bill

EXAMPLES = [
    "How many customers do we have in each country?",
    "What are the top 5 products by revenue?",
    "How many orders were placed in each month of 2025?",
    "Which customers have never placed an order?",
    "What is the weather in Paris?",
    "Show me every customer's email address",
]

st.set_page_config(page_title="Talk to your database", page_icon="💬")

# Create the sample database the first time (for example on a fresh deployment).
if not DB_PATH.exists():
    make_data.build_database()

# Remember how many questions this visitor has asked.
if "count" not in st.session_state:
    st.session_state["count"] = 0
if "question" not in st.session_state:
    st.session_state["question"] = ""

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Try an example")
    for example in EXAMPLES:
        if st.button(example):
            st.session_state["question"] = example

    st.header("The data")
    st.code(SCHEMA_TEXT, language="text")
    st.caption("Model: " + PROVIDER + " / " + MODEL)

# ── Main page ─────────────────────────────────────────────────────────────────
st.title("💬 Talk to your database")
st.write("Ask a question about a made-up online shop. The AI writes the SQL, a safety check approves it, "
         "and it runs **read-only**.")

problem = check_setup()
if problem != "":
    st.error(problem)
    st.stop()

question = st.text_input("Your question", key="question", placeholder="e.g. Which category earns the most?")
ask_clicked = st.button("Ask", type="primary")

if ask_clicked:
    if st.session_state["count"] >= MAX_QUESTIONS_PER_SESSION:
        st.warning("You have reached the limit of " + str(MAX_QUESTIONS_PER_SESSION) + " questions for this session.")
    else:
        st.session_state["count"] = st.session_state["count"] + 1
        with st.spinner("Thinking..."):
            result = ask(question)

        if result["status"] == "ok":
            st.success(result["answer"])

            with st.expander("The SQL that was run"):
                st.code(result["sql"], language="sql")

            table = pd.DataFrame(result["rows"], columns=result["columns"])
            st.dataframe(table, width="stretch")
            if result["was_cut_short"]:
                st.caption("Only the first 100 rows are shown.")

            # A bar chart makes sense for "a label and a number" with a handful of rows.
            if len(result["columns"]) == 2 and 2 <= len(table) <= 30 and pd.api.types.is_numeric_dtype(table.iloc[:, 1]):
                st.bar_chart(table.set_index(result["columns"][0]))

        elif result["status"] == "blocked":
            st.error(result["message"])
            if result["sql"] != "":
                with st.expander("The query that was refused"):
                    st.code(result["sql"], language="sql")

        else:
            st.warning(result["message"])

st.caption("Questions used: " + str(st.session_state["count"]) + " of " + str(MAX_QUESTIONS_PER_SESSION))
