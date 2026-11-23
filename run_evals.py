"""
run_evals.py - an exam for the app

It asks every question in evals/questions.py and checks the answer:
  - normal questions   : the rows the app returns must match the rows of our "gold" SQL
  - unanswerable ones  : the app must say "I can't answer that" (and not make something up)

Run it:
    python run_evals.py          all questions
    python run_evals.py 5        only the first 5 (a quick check)

It exits with an error if the score is below THRESHOLD, so you can use it as a release check.
"""

import sqlite3
import sys
import time

from evals.questions import QUESTIONS, UNANSWERABLE
from llm import MODEL, PROVIDER, check_setup
from main import ask
from schema import DB_PATH

THRESHOLD = 0.75        # the lowest score we accept
PAUSE_SECONDS = 1       # a short pause between questions, to be kind to free models


def clean(value):
    """Make a value easy to compare: numbers are rounded, everything else becomes text."""
    if isinstance(value, int) or isinstance(value, float):
        return round(float(value), 2)
    return str(value)


def clean_row(row):
    """Clean every value in a row."""
    cleaned = []
    for value in row:
        cleaned.append(clean(value))
    return cleaned


def contains_all(row, wanted):
    """True if every value in 'wanted' is somewhere in 'row'. (The app may add extra columns. That is fine.)"""
    for value in wanted:
        if value not in row:
            return False
    return True


def rows_match(gold_rows, app_rows):
    """Do the app's rows match the correct rows? Same number of rows, in any order."""
    if len(gold_rows) != len(app_rows):
        return False

    unused = []
    for row in app_rows:
        unused.append(clean_row(row))

    for gold in gold_rows:
        wanted = clean_row(gold)
        found = -1
        for position in range(len(unused)):
            if contains_all(unused[position], wanted):
                found = position
                break
        if found == -1:
            return False
        unused.pop(found)
    return True


def gold_rows_for(sql):
    """Run the human-written gold query to get the correct rows."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def main():
    problem = check_setup()
    if problem != "":
        raise SystemExit(problem)

    limit = len(QUESTIONS)
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    questions = QUESTIONS[:limit]

    print("Model: " + PROVIDER + " / " + MODEL + "\n")

    passed = 0
    failures = []
    for number in range(len(questions)):
        item = questions[number]
        result = ask(item["question"], explain_result=False)
        gold = gold_rows_for(item["gold_sql"])

        if result["status"] == "ok" and rows_match(gold, result["rows"]):
            passed = passed + 1
            print("PASS  " + str(number + 1).rjust(2) + "  " + item["question"][:80])
        else:
            print("FAIL  " + str(number + 1).rjust(2) + "  " + item["question"][:80])
            failures.append({"question": item["question"], "status": result["status"], "sql": result["sql"],
                             "app_rows": result["rows"][:3], "gold_rows": gold[:3], "message": result["message"]})
        time.sleep(PAUSE_SECONDS)

    # The questions the data cannot answer. The only right reaction is "I can't answer that".
    unanswerable_passed = 0
    unanswerable_total = 0
    if limit == len(QUESTIONS):
        for question in UNANSWERABLE:
            unanswerable_total = unanswerable_total + 1
            result = ask(question, explain_result=False)
            if result["status"] == "cannot_answer":
                unanswerable_passed = unanswerable_passed + 1
                print("PASS  --  (unanswerable) " + question)
            else:
                print("FAIL  --  (unanswerable) " + question)
                failures.append({"question": question, "status": result["status"], "sql": result["sql"],
                                 "app_rows": result["rows"][:3], "gold_rows": "should have refused", "message": result["message"]})
            time.sleep(PAUSE_SECONDS)

    total = len(questions) + unanswerable_total
    score = (passed + unanswerable_passed) / total
    print()
    print("Answerable questions   : " + str(passed) + " of " + str(len(questions)))
    print("Unanswerable questions : " + str(unanswerable_passed) + " of " + str(unanswerable_total))
    print("Score                  : " + format(score * 100, ".0f") + "%")

    if len(failures) > 0:
        print("\nWhat went wrong:")
        for failure in failures:
            print("  - " + failure["question"])
            print("      status: " + failure["status"] + "   sql: " + failure["sql"][:150])
            print("      the app returned: " + str(failure["app_rows"]) + "   correct: " + str(failure["gold_rows"]))

    if score < THRESHOLD:
        print("\nBELOW THE THRESHOLD of " + format(THRESHOLD * 100, ".0f") + "%. Do not release this.")
        sys.exit(1)


if __name__ == "__main__":
    main()
