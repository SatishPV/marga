from marga.catalog.profiler import build_catalog


def test_catalog_infers_relationship():
    catalog = build_catalog(["sample_data/customers.csv", "sample_data/orders.csv"])
    assert len(catalog["files"]) == 2
    assert any(
        r["from"].endswith("customer_id") and r["to"].endswith("id")
        for r in catalog["relationships"]
    )


def test_catalog_profiles_columns():
    catalog = build_catalog(["sample_data/customers.csv"])
    cols = {c["name"] for c in catalog["files"][0]["columns"]}
    assert cols == {"id", "name", "city"}
