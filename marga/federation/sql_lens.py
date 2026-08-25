"""
SQL lens: queries the ORIGINAL CSV/JSON files directly via DuckDB.
Nothing is migrated or copied into a database — DuckDB reads the files
in place for each query.
"""
import duckdb
import pandas as pd


def query(sql: str, file_bindings: dict[str, str]) -> pd.DataFrame:
    """
    file_bindings maps a view name -> file path, e.g.
    {"customers": "sample_data/customers.csv", "orders": "sample_data/orders.csv"}
    """
    con = duckdb.connect()
    for view_name, path in file_bindings.items():
        if path.endswith(".csv"):
            con.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_csv_auto('{path}')")
        elif path.endswith(".json"):
            con.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_json_auto('{path}')")
    return con.execute(sql).fetchdf()


if __name__ == "__main__":
    bindings = {
        "customers": "sample_data/customers.csv",
        "orders": "sample_data/orders.csv",
    }
    result = query(
        """
        SELECT c.name, c.city, o.order_id, o.amount
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        ORDER BY c.name
        """,
        bindings,
    )
    print(result)
