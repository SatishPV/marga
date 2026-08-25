-- Mirrors sample_data/customers.csv and orders.csv, so you can test the
-- SAME relationship marga infers from files against a live DB source.

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    amount NUMERIC(10, 2)
);

INSERT INTO customers (id, name, city) VALUES
    (1, 'Alice', 'Tampa'),
    (2, 'Bob', 'Austin'),
    (3, 'Carol', 'Denver');

INSERT INTO orders (order_id, customer_id, amount) VALUES
    (101, 1, 250.00),
    (102, 1, 80.00),
    (103, 2, 120.00),
    (104, 3, 60.00);
