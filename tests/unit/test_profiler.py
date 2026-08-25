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


def test_no_false_positive_relationship_from_id_naming_alone():
    """
    Regression test: an *_id column must not be matched to an unrelated
    file's `id` column just because the naming pattern looks right.
    products.product_id and customers.id happen to overlap numerically
    (both are small int ranges) but have no real relationship — this
    must not be reported.
    """
    catalog = build_catalog([
        "sample_data/customers.csv",
        "sample_data/products.csv",
    ])
    bogus = [
        r for r in catalog["relationships"]
        if "products.csv.product_id" in r["from"] and "customers.csv.id" in r["to"]
    ]
    assert bogus == [], f"Expected no spurious product_id->customers.id relationship, got {bogus}"


def test_parquet_and_arrow_round_trip(tmp_path):
    """Real files, real read — Parquet and Arrow (Feather) formats are
    now supported by the file adapter, verified end to end."""
    import pandas as pd
    df = pd.read_csv("sample_data/customers.csv")

    parquet_path = tmp_path / "customers.parquet"
    arrow_path = tmp_path / "customers.arrow"
    df.to_parquet(parquet_path)
    df.to_feather(arrow_path)

    from marga.sources.files.file_source import load_file
    df_parquet = load_file(str(parquet_path))
    df_arrow = load_file(str(arrow_path))

    assert list(df_parquet.columns) == list(df.columns)
    assert list(df_arrow.columns) == list(df.columns)
    assert len(df_parquet) == len(df)
    assert len(df_arrow) == len(df)
