"""
safety.py - the part that keeps the database safe

The AI model writes the SQL. We never trust it. Before anything runs, there are two layers:

  Layer 1: check_sql()    plain Python rules with friendly messages ("Only SELECT is allowed")
  Layer 2: run_query()    the database itself refuses anything dangerous, even if layer 1 has a gap:
                            - the file is opened READ-ONLY
                            - an "authorizer" blocks private columns and unknown tables
                            - a timer stops queries that run too long

The model can ask for anything. These rules do not listen to it.
"""

import re
import sqlite3
import time

from schema import ALLOWED_TABLES, BLOCKED_COLUMNS, DB_PATH

MAX_ROWS = 100      # we never return more rows than this
MAX_SECONDS = 5     # a query that runs longer than this is stopped

# Words that mean "change something". A question never needs them.
FORBIDDEN_WORDS = ["insert", "update", "delete", "drop", "alter", "create", "attach", "detach",
                   "pragma", "replace", "truncate", "vacuum", "reindex", "load_extension"]


# ---------------------------------------------------------------------------
# Layer 1: readable rules
# ---------------------------------------------------------------------------
def check_sql(sql):
    """Look at the SQL before it runs. Returns (True, "") if it is allowed, or (False, "the reason")."""
    text = sql.strip()

    # A single trailing semicolon is fine. Remove it.
    if text.endswith(";"):
        text = text[:-1].strip()

    if text == "":
        return False, "The query is empty."

    # Rule 1: one statement only. A second statement could be "DROP TABLE ...".
    if ";" in text:
        return False, "Only one statement is allowed."

    # Rule 2: no comments. Attackers hide things in them.
    if "--" in text or "/*" in text:
        return False, "Comments are not allowed."

    # Rule 3: it must start with SELECT (or WITH, which is a SELECT with a named helper table). That means read-only.
    lowered = text.lower()
    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False, "Only SELECT queries are allowed."

    # Rule 4: none of the "change something" words.
    words = re.findall(r"[a-z_]+", lowered)
    for word in FORBIDDEN_WORDS:
        if word in words:
            return False, "The word '" + word + "' is not allowed."

    # Rule 5: only the allowed tables. (A WITH query may also use the helper names it creates itself.)
    helper_names = re.findall(r"(?:with|,)\s+([a-z_]+)\s+as\s*\(", lowered)
    tables_used = re.findall(r"\b(?:from|join)\s+([a-z_]+)", lowered)
    for table in tables_used:
        if table not in ALLOWED_TABLES and table not in helper_names:
            return False, "The table '" + table + "' is not available."

    # Rule 6: never mention a private column.
    for table in BLOCKED_COLUMNS:
        for column in BLOCKED_COLUMNS[table]:
            if column in words:
                return False, "The column '" + column + "' is private."

    return True, ""


# ---------------------------------------------------------------------------
# Layer 2: the database enforces the rules itself
# ---------------------------------------------------------------------------
def authorizer(action, arg1, arg2, db_name, source):
    """SQLite calls this for EVERY step of a query and asks: is this allowed?
    We say yes to reading the allowed tables, and no to everything else."""
    if action == sqlite3.SQLITE_SELECT or action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK

    if action == sqlite3.SQLITE_READ:
        table = arg1
        column = arg2
        if table not in ALLOWED_TABLES:
            return sqlite3.SQLITE_DENY
        if column in BLOCKED_COLUMNS.get(table, []):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    return sqlite3.SQLITE_DENY    # writes, pragmas, attaching files... all refused


def make_timer():
    """Returns a function that SQLite calls again and again while a query runs.
    When it returns 1, SQLite stops the query."""
    started = time.time()

    def stop_if_too_slow():
        if time.time() - started > MAX_SECONDS:
            return 1
        return 0

    return stop_if_too_slow


def open_read_only():
    """Open the database so that nothing can be changed, whatever the SQL says."""
    address = DB_PATH.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(address, uri=True)
    conn.set_authorizer(authorizer)
    conn.set_progress_handler(make_timer(), 10000)
    return conn


def run_query(sql):
    """Run a query safely. Returns (column names, rows, was_cut_short).
    Raises sqlite3.Error if the database refuses it or the SQL is wrong."""
    conn = open_read_only()
    try:
        cursor = conn.execute(sql)

        columns = []
        for item in cursor.description:
            columns.append(item[0])

        rows = cursor.fetchmany(MAX_ROWS + 1)      # one extra row tells us if there was more
        was_cut_short = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        return columns, rows, was_cut_short
    finally:
        conn.close()
