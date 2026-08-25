"""
Seeds Elasticsearch with the same customers/orders relationship as
the Postgres and MongoDB seeds — for a genuine cross-source-type test.

Run from your host machine (auto-loads .env.host if present):
    python3 docker/seed/seed_es.py
"""
import os

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv(".env.host")
host = os.environ.get("MARGA_ELASTICSEARCH_HOST", "http://localhost:9200")
es = Elasticsearch(hosts=[host])

es.indices.delete(index="customers", ignore_unavailable=True)
es.indices.delete(index="orders", ignore_unavailable=True)

customers = [
    {"id": 1, "name": "Alice", "city": "Tampa"},
    {"id": 2, "name": "Bob", "city": "Austin"},
    {"id": 3, "name": "Carol", "city": "Denver"},
]
orders = [
    {"order_id": 101, "customer_id": 1, "amount": 250.00},
    {"order_id": 102, "customer_id": 1, "amount": 80.00},
    {"order_id": 103, "customer_id": 2, "amount": 120.00},
    {"order_id": 104, "customer_id": 3, "amount": 60.00},
]

for doc in customers:
    es.index(index="customers", document=doc)
for doc in orders:
    es.index(index="orders", document=doc)

es.indices.refresh(index="customers")
es.indices.refresh(index="orders")

print(f"Seeded {len(customers)} customers, {len(orders)} orders into Elasticsearch")
