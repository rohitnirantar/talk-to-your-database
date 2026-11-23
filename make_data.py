"""
make_data.py - builds the sample shop database (shop.db)

All the data is made up. It uses a fixed random seed, so you get exactly the same
database every time you run this. That is what makes the evals repeatable.

Run it:  python make_data.py
"""

import random
import sqlite3
from datetime import date, timedelta

from schema import DB_PATH

FIRST_NAMES = ["Asha", "Ben", "Chen", "Dina", "Eli", "Farah", "Gus", "Hana", "Ivan", "Jia",
               "Kofi", "Lena", "Mateo", "Nora", "Omar", "Priya", "Quinn", "Rosa", "Sam", "Tara"]
LAST_NAMES = ["Adams", "Brown", "Clark", "Diaz", "Evans", "Fox", "Gupta", "Hill", "Ito", "Jones",
              "Khan", "Lopez", "Moore", "Nair", "Ortiz", "Patel", "Reed", "Singh", "Tan", "Wong"]
CITIES = [("Toronto", "Canada"), ("Vancouver", "Canada"), ("New York", "USA"), ("Austin", "USA"),
          ("London", "UK"), ("Manchester", "UK"), ("Mumbai", "India"), ("Delhi", "India"),
          ("Sydney", "Australia"), ("Berlin", "Germany")]
PRODUCTS = [
    ("Wireless Headphones", "Electronics", 79.00), ("4K Television", "Electronics", 250.00),
    ("Smart Watch", "Electronics", 129.00), ("Phone Charger", "Electronics", 19.00),
    ("Coffee Grinder", "Home", 45.00), ("Desk Lamp", "Home", 32.00),
    ("Cookware Set", "Home", 110.00), ("Throw Blanket", "Home", 28.00),
    ("Running Shoes", "Sports", 120.00), ("Yoga Mat", "Sports", 24.00),
    ("Dumbbell Set", "Sports", 85.00), ("Water Bottle", "Sports", 12.00),
    ("Mystery Novel", "Books", 14.00), ("Cookbook", "Books", 22.00),
    ("Science Textbook", "Books", 60.00), ("Children's Story Book", "Books", 9.00),
    ("Rain Jacket", "Clothing", 95.00), ("Denim Jeans", "Clothing", 55.00),
    ("Cotton T-Shirt", "Clothing", 18.00), ("Wool Socks", "Clothing", 11.00),
]
STATUSES = ["completed", "completed", "completed", "completed", "completed", "shipped", "cancelled"]


def random_date(start, end):
    """A random date between two dates, as text like '2025-03-15'."""
    days = (end - start).days
    return (start + timedelta(days=random.randint(0, days))).isoformat()


def build_database():
    """Create shop.db from scratch."""
    random.seed(42)  # the same data every time

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)

    # --- the four tables ---
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, email TEXT, city TEXT, country TEXT, signup_date TEXT)")
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL)")
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT)")
    conn.execute("CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER, product_id INTEGER, quantity INTEGER, unit_price REAL)")

    # --- customers: 60 of them. The email is private data. ---
    for customer_id in range(1, 61):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        city, country = random.choice(CITIES)
        email = first.lower() + "." + last.lower() + str(customer_id) + "@example.com"
        signup = random_date(date(2024, 1, 1), date(2024, 12, 31))
        conn.execute("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)",
                     (customer_id, first + " " + last, email, city, country, signup))

    # --- products ---
    for number in range(len(PRODUCTS)):
        name, category, price = PRODUCTS[number]
        conn.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (number + 1, name, category, price))

    # --- orders: 400 of them, each with 1 to 4 items. Customers 56 to 60 never order. ---
    item_id = 1
    for order_id in range(1, 401):
        customer_id = random.randint(1, 55)
        order_date = random_date(date(2025, 1, 1), date(2025, 12, 31))
        status = random.choice(STATUSES)
        conn.execute("INSERT INTO orders VALUES (?, ?, ?, ?)", (order_id, customer_id, order_date, status))

        for line in range(random.randint(1, 4)):
            product_number = random.randint(0, len(PRODUCTS) - 1)
            price = PRODUCTS[product_number][2]
            quantity = random.randint(1, 3)
            conn.execute("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)",
                         (item_id, order_id, product_number + 1, quantity, price))
            item_id = item_id + 1

    conn.commit()
    conn.close()
    print("Created " + str(DB_PATH.name) + ": 60 customers, " + str(len(PRODUCTS)) + " products, 400 orders, " + str(item_id - 1) + " order items")


if __name__ == "__main__":
    build_database()
