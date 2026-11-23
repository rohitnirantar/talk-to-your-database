"""
main.py - the whole pipeline: a question goes in, a safe answer comes out

    Question -> [1] AI writes SQL -> [2] safety checks -> [3] run it read-only -> [4] AI explains the rows

Try it in the terminal:   python main.py
The web app (frontend.py) uses the same ask() function.
"""

import json
import sqlite3

import make_data
from llm import ask_model, check_setup, ModelUnavailable, MODEL, PROVIDER
from safety import check_sql, run_query
from schema import DB_PATH, SCHEMA_TEXT

MAX_QUESTION_LENGTH = 300

# Instructions for step 1: write the SQL.
SQL_INSTRUCTIONS = """You turn questions about an online shop into one SQLite query.

""" + SCHEMA_TEXT + """
Rules:
  - Write ONE SELECT query. Never change data.
  - Use only the tables and columns listed above.
  - If the question cannot be answered with this data, say so. Do not guess.
  - Give each column a clear name with AS.

Reply with ONLY a JSON object, nothing else, in this form:
{"can_answer": true, "sql": "SELECT ...", "reason": "one short sentence"}
or, if the data cannot answer it:
{"can_answer": false, "sql": "", "reason": "why not"}
"""


# ---------------------------------------------------------------------------
# Step 1: the AI writes the SQL
# ---------------------------------------------------------------------------
def read_json(text):
    """Pull the JSON object out of the model's reply. Models sometimes add words or ```json fences around it."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def write_sql(question, last_sql="", last_error=""):
    """Ask the model for SQL. Returns a dictionary with can_answer, sql and reason."""
    user_text = question
    if last_error != "":
        # Second attempt: show the model what went wrong, so it can fix its own query.
        user_text = question + "\n\nYour previous query was:\n" + last_sql + "\nIt failed with: " + last_error + "\nPlease fix it."

    reply = ask_model(SQL_INSTRUCTIONS, user_text)
    answer = read_json(reply)

    if answer is None:
        return {"can_answer": False, "sql": "", "reason": "The model did not reply in the expected format."}

    sql = answer.get("sql")
    if sql is None:
        sql = ""
    return {"can_answer": bool(answer.get("can_answer")), "sql": sql, "reason": str(answer.get("reason", ""))}


# ---------------------------------------------------------------------------
# Step 4: the AI explains the rows
# ---------------------------------------------------------------------------
def explain(question, columns, rows):
    """Write a short plain-English answer, using only the rows we actually got."""
    if len(rows) == 0:
        return "The query ran, but it returned no rows."

    lines = [", ".join(columns)]
    for row in rows[:20]:
        values = []
        for value in row:
            values.append(str(value))
        lines.append(", ".join(values))

    instructions = ("You explain database results to a shop manager. Answer the question in at most 2 short sentences. "
                    "Use ONLY the numbers and names in the rows. Never invent anything.")
    user_text = "Question: " + question + "\n\nRows:\n" + "\n".join(lines)
    return ask_model(instructions, user_text).strip()


# ---------------------------------------------------------------------------
# The whole pipeline
# ---------------------------------------------------------------------------
def ask(question, explain_result=True):
    """Answer one question. Returns a dictionary:
         status  : "ok", "cannot_answer", "blocked", "error" or "rejected"
         message : a sentence for the user when the status is not "ok"
         sql, columns, rows, was_cut_short, answer : filled in when it worked
    """
    result = {"status": "", "message": "", "sql": "", "columns": [], "rows": [], "was_cut_short": False, "answer": ""}

    question = question.strip()
    if question == "":
        result["status"] = "rejected"
        result["message"] = "Please type a question."
        return result
    if len(question) > MAX_QUESTION_LENGTH:
        result["status"] = "rejected"
        result["message"] = "That question is too long. Please keep it under " + str(MAX_QUESTION_LENGTH) + " characters."
        return result

    last_sql = ""
    last_error = ""
    for attempt in range(2):     # one retry, only for SQL that fails to run
        try:
            written = write_sql(question, last_sql, last_error)
        except ModelUnavailable as problem:
            result["status"] = "error"
            result["message"] = str(problem)
            return result

        if not written["can_answer"] or written["sql"].strip() == "":
            result["status"] = "cannot_answer"
            result["message"] = "I can't answer that from this data. " + written["reason"]
            return result

        sql = written["sql"].strip()
        result["sql"] = sql

        # Step 2: the safety rules. A refusal here is final. We do not let the model try again.
        allowed, reason = check_sql(sql)
        if not allowed:
            result["status"] = "blocked"
            result["message"] = "I won't run that query. " + reason
            return result

        # Step 3: run it, read-only.
        try:
            columns, rows, was_cut_short = run_query(sql)
        except sqlite3.OperationalError as error:
            # A normal SQL mistake (for example "no such column"), or the timer stopped a slow query.
            if "interrupted" in str(error):
                result["status"] = "error"
                result["message"] = "That query took too long, so it was stopped."
                return result
            last_sql = sql
            last_error = str(error)
            continue           # give the model one more try
        except sqlite3.DatabaseError:
            # The database itself refused: a private column, an unknown table, or a write.
            result["status"] = "blocked"
            result["message"] = "I won't run that query. It tried to read or change something that is not allowed."
            return result

        result["status"] = "ok"
        result["columns"] = columns
        result["rows"] = rows
        result["was_cut_short"] = was_cut_short
        if explain_result:
            try:
                result["answer"] = explain(question, columns, rows)
            except ModelUnavailable:
                result["answer"] = "(The explanation is not available right now, but the rows below are correct.)"
        return result

    result["status"] = "error"
    result["message"] = "I could not write a working query for that. Last error: " + last_error
    return result


# ---------------------------------------------------------------------------
# Terminal chat
# ---------------------------------------------------------------------------
def show(result):
    """Print one result in the terminal."""
    if result["status"] != "ok":
        print("\n[" + result["status"] + "] " + result["message"])
        if result["sql"] != "":
            print("SQL: " + result["sql"])
        return

    print("\nSQL: " + result["sql"])
    print(" | ".join(result["columns"]))
    for row in result["rows"][:15]:
        values = []
        for value in row:
            values.append(str(value))
        print(" | ".join(values))
    if len(result["rows"]) > 15:
        print("... (" + str(len(result["rows"])) + " rows in total)")
    print("\nAnswer: " + result["answer"])


if __name__ == "__main__":
    problem = check_setup()
    if problem != "":
        raise SystemExit(problem)
    if not DB_PATH.exists():
        make_data.build_database()

    print("Talk to your database  (model: " + PROVIDER + " / " + MODEL + ")")
    print("Type a question about the shop, or 'quit' to stop.\n")
    while True:
        question = input("You: ")
        if question.strip().lower() in ["quit", "exit", "q"]:
            break
        show(ask(question))
        print()
