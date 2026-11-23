"""
evals/questions.py - the test questions, each with a correct "gold" SQL query written by a human

An eval works like an exam:
  1. we ask the app the question
  2. we run the gold SQL ourselves to get the correct rows
  3. we compare the rows the app got with the correct rows

We compare ROWS, not SQL text, because two very different queries can give the same right answer.
"""

# Revenue per order item, written once so the questions below stay short.
REVENUE = "SUM(oi.quantity * oi.unit_price)"
NOT_CANCELLED = "o.status != 'cancelled'"

# Questions the data CAN answer. Each has a gold query.
QUESTIONS = [
    {"question": "How many customers do we have?",
     "gold_sql": "SELECT COUNT(*) FROM customers"},

    {"question": "How many products are in each category?",
     "gold_sql": "SELECT category, COUNT(*) FROM products GROUP BY category"},

    {"question": "What is the most expensive product? Give its name and price.",
     "gold_sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 1"},

    {"question": "How many orders were placed in March 2025?",
     "gold_sql": "SELECT COUNT(*) FROM orders WHERE order_date >= '2025-03-01' AND order_date < '2025-04-01'"},

    {"question": "How many orders were cancelled?",
     "gold_sql": "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"},

    {"question": "What is the total revenue from completed orders only?",
     "gold_sql": "SELECT " + REVENUE + " FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE o.status = 'completed'"},

    {"question": "What is the total revenue, leaving out cancelled orders?",
     "gold_sql": "SELECT " + REVENUE + " FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE " + NOT_CANCELLED},

    {"question": "Who are the top 5 customers by total spending, leaving out cancelled orders? Give the name and the total.",
     "gold_sql": "SELECT c.name, " + REVENUE + " FROM customers c JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id WHERE " + NOT_CANCELLED + " GROUP BY c.id ORDER BY 2 DESC LIMIT 5"},

    {"question": "Which product category has the highest revenue, leaving out cancelled orders? Give the category and the revenue.",
     "gold_sql": "SELECT p.category, " + REVENUE + " FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id WHERE " + NOT_CANCELLED + " GROUP BY p.category ORDER BY 2 DESC LIMIT 1"},

    {"question": "How many customers are there in each country?",
     "gold_sql": "SELECT country, COUNT(*) FROM customers GROUP BY country"},

    {"question": "What is the average order value for completed orders?",
     "gold_sql": "SELECT AVG(total) FROM (SELECT o.id, " + REVENUE + " AS total FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE o.status = 'completed' GROUP BY o.id)"},

    {"question": "How many orders were placed in each month of 2025? Give the month as YYYY-MM and the count.",
     "gold_sql": "SELECT strftime('%Y-%m', order_date), COUNT(*) FROM orders GROUP BY 1"},

    {"question": "Which product sold the most units, leaving out cancelled orders? Give the product name and the units.",
     "gold_sql": "SELECT p.name, SUM(oi.quantity) FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id WHERE " + NOT_CANCELLED + " GROUP BY p.id ORDER BY 2 DESC LIMIT 1"},

    {"question": "Which customers have never placed an order? Give their names.",
     "gold_sql": "SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM orders)"},

    {"question": "How many customers placed more than 8 orders?",
     "gold_sql": "SELECT COUNT(*) FROM (SELECT customer_id FROM orders GROUP BY customer_id HAVING COUNT(*) > 8)"},

    {"question": "How many Electronics items were sold in total, leaving out cancelled orders?",
     "gold_sql": "SELECT SUM(oi.quantity) FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id WHERE p.category = 'Electronics' AND " + NOT_CANCELLED},

    {"question": "Which city has the most customers? Give the city and the number of customers.",
     "gold_sql": "SELECT city, COUNT(*) FROM customers GROUP BY city ORDER BY 2 DESC LIMIT 1"},

    {"question": "How many orders did customers from Canada place?",
     "gold_sql": "SELECT COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id WHERE c.country = 'Canada'"},

    {"question": "What is the cheapest product in the Sports category? Give its name and price.",
     "gold_sql": "SELECT name, price FROM products WHERE category = 'Sports' ORDER BY price ASC LIMIT 1"},

    {"question": "How many customers signed up in the first half of 2024 (January to June)?",
     "gold_sql": "SELECT COUNT(*) FROM customers WHERE signup_date >= '2024-01-01' AND signup_date < '2024-07-01'"},

    {"question": "What is the revenue of each product category, leaving out cancelled orders?",
     "gold_sql": "SELECT p.category, " + REVENUE + " FROM order_items oi JOIN orders o ON o.id = oi.order_id JOIN products p ON p.id = oi.product_id WHERE " + NOT_CANCELLED + " GROUP BY p.category"},

    {"question": "What is the date of the most recent order?",
     "gold_sql": "SELECT MAX(order_date) FROM orders"},

    {"question": "How many different products have been ordered at least once?",
     "gold_sql": "SELECT COUNT(DISTINCT product_id) FROM order_items"},

    {"question": "What is the average price of the products in each category?",
     "gold_sql": "SELECT category, AVG(price) FROM products GROUP BY category"},

    {"question": "Which 3 months of 2025 had the most orders? Give the month as YYYY-MM and the count.",
     "gold_sql": "SELECT strftime('%Y-%m', order_date), COUNT(*) FROM orders GROUP BY 1 ORDER BY 2 DESC LIMIT 3"},

    {"question": "What was the total revenue in the first quarter of 2025 (January to March), leaving out cancelled orders?",
     "gold_sql": "SELECT " + REVENUE + " FROM order_items oi JOIN orders o ON o.id = oi.order_id WHERE " + NOT_CANCELLED + " AND o.order_date >= '2025-01-01' AND o.order_date < '2025-04-01'"},
]

# Questions the data CANNOT answer. The right behaviour is to say so, not to invent something.
UNANSWERABLE = [
    "What is the weather in Paris today?",
    "What is our profit margin on each product?",
    "Which customers are unhappy with their orders?",
    "How many employees work at the shop?",
]
