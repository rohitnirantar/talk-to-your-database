"""
test_safety.py - tests for the safety checks. No AI model is used, so this is free and instant.

Run it:  python test_safety.py
(It also works with pytest, because every test is a function that starts with "test_".)
"""

import sqlite3
import sys

import main
import make_data
from schema import DB_PATH
from safety import check_sql, run_query

# Queries that are fine
GOOD_QUERIES = [
    "SELECT COUNT(*) FROM customers",
    "SELECT name, price FROM products ORDER BY price DESC LIMIT 3;",
    "SELECT c.name, SUM(oi.quantity * oi.unit_price) FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id GROUP BY c.name",
    "SELECT strftime('%Y-%m', order_date), COUNT(*) FROM orders GROUP BY 1",
    "WITH totals AS (SELECT order_id, SUM(quantity) AS units FROM order_items GROUP BY order_id) SELECT AVG(units) FROM totals",
]

# Queries that must be refused by check_sql (layer 1)
BAD_QUERIES = [
    "DROP TABLE orders",
    "DELETE FROM orders",
    "UPDATE products SET price = 0",
    "INSERT INTO customers (name) VALUES ('Evil')",
    "SELECT * FROM orders; DROP TABLE orders",
    "SELECT 1; SELECT 2",
    "SELECT email FROM customers",
    "SELECT name FROM sqlite_master",
    "SELECT * FROM secrets",
    "PRAGMA table_info(customers)",
    "ATTACH DATABASE 'other.db' AS other",
    "CREATE TABLE backup AS SELECT * FROM orders",
    "SELECT 1 -- hidden comment",
    "SELECT /* sneaky */ 1",
    "WITH x AS (SELECT 1) DELETE FROM orders",
    "WITH x AS (SELECT email FROM customers) SELECT * FROM x",
    "",
]

# Queries that sneak past layer 1 on purpose. The database itself (layer 2) must stop them.
SNEAKY_QUERIES = [
    "SELECT * FROM customers",                              # the star includes the private email column
    "SELECT c.* FROM customers c",                          # same, with an alias
    "SELECT name FROM customers, sqlite_master",            # a second table hidden after a comma
    "SELECT (SELECT email FROM customers LIMIT 1)",         # (also caught by layer 1, but layer 2 must hold alone)
]


def test_good_queries_are_allowed():
    for sql in GOOD_QUERIES:
        allowed, reason = check_sql(sql)
        assert allowed, "should be allowed: " + sql + " (" + reason + ")"


def test_bad_queries_are_refused():
    for sql in BAD_QUERIES:
        allowed, reason = check_sql(sql)
        assert not allowed, "should be refused: " + sql


def test_database_refuses_sneaky_queries():
    for sql in SNEAKY_QUERIES:
        try:
            run_query(sql)
        except sqlite3.Error:
            continue                       # the database said no. Good.
        assert False, "the database should have refused: " + sql


def test_database_is_read_only():
    # We skip layer 1 on purpose and talk to layer 2 directly.
    for sql in ["DELETE FROM orders", "UPDATE products SET price = 0", "DROP TABLE orders"]:
        try:
            run_query(sql)
        except sqlite3.Error:
            continue
        assert False, "the database should have refused: " + sql

    columns, rows, cut = run_query("SELECT COUNT(*) FROM orders")
    assert rows[0][0] == 400, "the orders table should be untouched"


def test_good_query_runs_and_rows_are_limited():
    columns, rows, cut = run_query("SELECT id, name FROM customers")
    assert columns == ["id", "name"]
    assert len(rows) == 60 and not cut

    columns, rows, cut = run_query("SELECT id FROM order_items")
    assert len(rows) == 100 and cut, "more than 100 rows must be cut short"


def test_slow_query_is_stopped():
    slow = ("SELECT COUNT(*) FROM order_items a, order_items b, order_items c, order_items d")
    try:
        run_query(slow)
    except sqlite3.Error:
        return
    assert False, "the slow query should have been stopped by the timer"


def test_with_query_runs():
    # This is the query shape that the exam found being wrongly refused. It must run now.
    sql = ("WITH order_totals AS (SELECT o.id, SUM(oi.quantity * oi.unit_price) AS order_total "
           "FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE o.status = 'completed' GROUP BY o.id) "
           "SELECT AVG(order_total) AS average_order_value FROM order_totals")
    allowed, reason = check_sql(sql)
    assert allowed, reason
    columns, rows, cut = run_query(sql)
    assert round(rows[0][0], 2) == 306.33


def test_pipeline_survives_a_misbehaving_model():
    # We replace the AI with a fake one that ALWAYS returns dangerous SQL, to prove that the code around it holds.
    dangerous = ["DROP TABLE orders", "DELETE FROM customers", "SELECT * FROM customers",
                 "SELECT email FROM customers", "SELECT 1; DROP TABLE orders"]
    real_write_sql = main.write_sql
    try:
        for sql in dangerous:
            def fake_write_sql(question, last_sql="", last_error="", bad_sql=sql):
                return {"can_answer": True, "sql": bad_sql, "reason": "fake"}

            main.write_sql = fake_write_sql
            result = main.ask("anything", explain_result=False)
            assert result["status"] == "blocked", "should be blocked: " + sql
            assert result["rows"] == [], "no rows may come back for: " + sql
    finally:
        main.write_sql = real_write_sql

    columns, rows, cut = run_query("SELECT COUNT(*) FROM customers")
    assert rows[0][0] == 60, "the database must be untouched"


def main_tests():
    if not DB_PATH.exists():
        make_data.build_database()

    tests = [test_good_queries_are_allowed, test_bad_queries_are_refused, test_database_refuses_sneaky_queries,
             test_database_is_read_only, test_good_query_runs_and_rows_are_limited, test_slow_query_is_stopped,
             test_with_query_runs, test_pipeline_survives_a_misbehaving_model]
    failed = 0
    for test in tests:
        try:
            test()
            print("PASS  " + test.__name__)
        except AssertionError as error:
            failed = failed + 1
            print("FAIL  " + test.__name__ + "  " + str(error))

    print()
    print(str(len(tests) - failed) + " of " + str(len(tests)) + " tests passed")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main_tests()
