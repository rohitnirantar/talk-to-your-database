"""
schema.py - everything the program knows about the database

Three things live here:
  1. where the database file is
  2. which tables and columns the app may touch (the "allow list")
  3. a plain-English description of the tables, which we show to the AI model
"""

from pathlib import Path

# The database is one file, next to this script. make_data.py creates it.
DB_PATH = Path(__file__).parent / "shop.db"

# The AI may only read these tables.
ALLOWED_TABLES = ["customers", "products", "orders", "order_items"]

# Columns that are private. Nobody can read them through this app.
BLOCKED_COLUMNS = {
    "customers": ["email"],
}

# What we tell the AI about the database.
# Note: the private email column is NOT mentioned here, so the AI does not even know it exists.
SCHEMA_TEXT = """
The database is SQLite. It has four tables:

customers(id, name, city, country, signup_date)
products(id, name, category, price)
orders(id, customer_id, order_date, status)
order_items(id, order_id, product_id, quantity, unit_price)

How the tables connect:
  orders.customer_id      = customers.id
  order_items.order_id    = orders.id
  order_items.product_id  = products.id

Notes:
  - Dates are text like '2025-03-15'. To group by month use strftime('%Y-%m', order_date).
  - orders.status is one of: 'completed', 'shipped', 'cancelled'.
  - Product categories are: Electronics, Home, Sports, Books, Clothing.
  - Revenue means SUM(order_items.quantity * order_items.unit_price).
  - Unless the question says otherwise, leave out cancelled orders when you calculate revenue.
  - Customers have private contact details that are not available.
"""
