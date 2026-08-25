"""
Seeds MongoDB with the same customers/orders relationship as
docker/postgres/init/01_seed.sql — so scanning Postgres, MongoDB, and
the CSV files together shows the SAME logical relationship across three
different source types, a genuine test of cross-source-type inference.

Run from your host machine (uses the mapped port, not the internal
Docker network). Reads credentials from the same MARGA_MONGODB_* env
vars as the CLI — auto-loads .env.host if present:
    python3 docker/seed/seed_mongo.py
"""
import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(".env.host")

host = os.environ.get("MARGA_MONGODB_HOST", "localhost")
port = os.environ.get("MARGA_MONGODB_PORT", "27017")
user = os.environ.get("MARGA_MONGODB_USER", "marga")
password = os.environ.get("MARGA_MONGODB_PASSWORD", "marga")
db_name = os.environ.get("MARGA_MONGODB_DBNAME", "marga_demo")

client = MongoClient(f"mongodb://{user}:{password}@{host}:{port}/?authSource=admin")
db = client[db_name]

db.customers.drop()
db.orders.drop()

db.customers.insert_many([
    {"id": 1, "name": "Alice", "city": "Tampa"},
    {"id": 2, "name": "Bob", "city": "Austin"},
    {"id": 3, "name": "Carol", "city": "Denver"},
])

db.orders.insert_many([
    {"order_id": 101, "customer_id": 1, "amount": 250.00},
    {"order_id": 102, "customer_id": 1, "amount": 80.00},
    {"order_id": 103, "customer_id": 2, "amount": 120.00},
    {"order_id": 104, "customer_id": 3, "amount": 60.00},
])

print(f"Seeded {db.customers.count_documents({})} customers, {db.orders.count_documents({})} orders")
