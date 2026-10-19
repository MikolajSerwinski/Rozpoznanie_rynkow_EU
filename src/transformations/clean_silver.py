import json
from pathlib import Path
import polars as pl
from src.config import RAW_DIR, SILVER_DIR, EU_COUNTRIES


def parse_jsonstat(data: dict) -> pl.DataFrame:
    """Uniwersalny dekoder formatu JSON-stat 2.0 (Eurostat / Comext) do Polars DataFrame."""
    dim_ids = data.get("id", [])
    sizes = data.get("size", [])
    values = data.get("value", {})
    dimensions = data.get("dimension", {})

    if not values or not dim_ids:
        return pl.DataFrame()

    # Mapowanie pozycji (indeksu) na kod tekstowy dla każdego wymiaru
    idx_to_code = []
    dim_labels = {}
    for dim in dim_ids:
        cat = dimensions[dim]["category"]
        index_map = cat["index"]
        if isinstance(index_map, dict):
            inv_map = {int(v): k for k, v in index_map.items()}
        else:
            inv_map = {i: k for i, k in enumerate(index_map)}
        idx_to_code.append(inv_map)
        dim_labels[dim] = cat.get("label", {})

    # Wyliczenie mnożników (strides) do odkodowania płaskiego indeksu JSON-stat
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    rows = []
    # Obsługa sytuacji, gdy 'value' w JSON-stat jest listą zamiast słownikiem
    items = values.items() if isinstance(values, dict) else enumerate(values)

    for flat_idx, val in items:
        if val is None:
            continue
        rem = int(flat_idx)
        row = {}
        for i, dim in enumerate(dim_ids):
            coord = rem // strides[i]
            rem = rem % strides[i]
            code = idx_to_code[i][coord]
            row[dim.lower()] = code
        row["value"] = float(val)
        rows.append(row)

    return pl.DataFrame(rows)


def clean_nbp() -> None:
    """Transformacja dziennych kursów NBP do średnich miesięcznych."""
    nbp_dir = RAW_DIR / "nbp"
    rows = []
    for file in sorted(nbp_dir.glob("eur_pln_*.json")):
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for rate in data.get("rates", []):
                rows.append({
                    "effective_date": rate["effectiveDate"],
                    "eur_pln": float(rate["mid"]),
                })

    df = pl.DataFrame(rows)
    df_monthly = (
        df.with_columns(
            pl.col("effective_date").str.slice(0, 7).alias("period"),
            pl.col("effective_date").str.slice(0, 4).cast(pl.Int32).alias("year"),
        )
        .group_by(["period", "year"])
        .agg([
            pl.col("eur_pln").mean().round(4).alias("avg_eur_pln"),
            pl.col("eur_pln").min().round(4).alias("min_eur_pln"),
            pl.col("eur_pln").max().round(4).alias("max_eur_pln"),
            pl.col("eur_pln").count().alias("trading_days"),
        ])
        .sort("period")
    )

    out_path = SILVER_DIR / "nbp_monthly.parquet"
    df_monthly.write_parquet(out_path)
    print(f"[Silver] Zapisano kursy miesięczne NBP ({len(df_monthly)} wierszy) -> {out_path}")


def clean_macro() -> None:
    """Transformacja danych o PKB per capita i ludności z Eurostatu."""
    macro_dir = RAW_DIR / "eurostat_macro"

    with open(macro_dir / "population_raw.json", "r", encoding="utf-8") as f:
        df_pop = parse_jsonstat(json.load(f))
    with open(macro_dir / "gdp_per_capita_raw.json", "r", encoding="utf-8") as f:
        df_gdp = parse_jsonstat(json.load(f))

    df_pop_clean = (
        df_pop.filter(pl.col("geo").is_in(EU_COUNTRIES))
        .select([
            pl.col("geo").alias("country_code"),
            pl.col("time").cast(pl.Int32).alias("year"),
            pl.col("value").cast(pl.Int64).alias("population"),
        ])
    )

    df_gdp_clean = (
        df_gdp.filter(pl.col("geo").is_in(EU_COUNTRIES))
        .select([
            pl.col("geo").alias("country_code"),
            pl.col("time").cast(pl.Int32).alias("year"),
            pl.col("value").cast(pl.Float64).alias("gdp_per_capita_eur"),
        ])
    )

    # Łączymy po kraju i roku, a dla najnowszych lat (np. 2026) uzupełniamy ostatnią znaną wartością (forward fill)
    years = pl.DataFrame({"year": list(range(2022, 2027))})
    countries = pl.DataFrame({"country_code": EU_COUNTRIES})
    grid = countries.join(years, how="cross")

    df_macro = (
        grid.join(df_pop_clean, on=["country_code", "year"], how="left")
        .join(df_gdp_clean, on=["country_code", "year"], how="left")
        .sort(["country_code", "year"])
        .with_columns([
            pl.col("population").forward_fill().backward_fill().over("country_code"),
            pl.col("gdp_per_capita_eur").forward_fill().backward_fill().over("country_code"),
        ])
    )

    out_path = SILVER_DIR / "macro_countries.parquet"
    df_macro.write_parquet(out_path)
    print(f"[Silver] Zapisano dane makroekonomiczne ({len(df_macro)} wierszy) -> {out_path}")


def clean_comext() -> None:
    """Transformacja danych handlowych Comext i przeliczenie jednostek masy na kg."""
    comext_dir = RAW_DIR / "comext"
    dfs = []

    for file in sorted(comext_dir.glob("comext_import_*.json")):
        with open(file, "r", encoding="utf-8") as f:
            df_part = parse_jsonstat(json.load(f))
            if not df_part.is_empty():
                dfs.append(df_part)

    if not dfs:
        raise ValueError("Brak danych Comext w warstwie raw!")

    df_raw = pl.concat(dfs, how="diagonal")

    # Ujednolicenie nazwy kolumny ze wskaźnikiem (indicators vs indicator)
    ind_col = "indicators" if "indicators" in df_raw.columns else "indicator"

    # Pivot wskaźników VALUE_IN_EUROS oraz QUANTITY_IN_100KG do osobnych kolumn
    df_pivoted = (
        df_raw.pivot(
            values="value",
            index=["reporter", "partner", "product", "time"],
            on=ind_col,
            aggregate_function="first",
        )
        .rename({
            "reporter": "importer_country",
            "partner": "partner_country",
            "product": "cn_code",
            "time": "period",
        })
    )

    # Upewnienie się, że obie kolumny miar istnieją
    if "VALUE_IN_EUROS" not in df_pivoted.columns:
        df_pivoted = df_pivoted.with_columns(pl.lit(0.0).alias("VALUE_IN_EUROS"))
    if "QUANTITY_IN_100KG" not in df_pivoted.columns:
        df_pivoted = df_pivoted.with_columns(pl.lit(0.0).alias("QUANTITY_IN_100KG"))

    # Czyszczenie i przeliczenie 100 kg -> 1 kg
    df_clean = (
        df_pivoted.with_columns([
            pl.col("period").str.slice(0, 4).cast(pl.Int32).alias("year"),
            pl.col("VALUE_IN_EUROS").fill_null(0.0).alias("value_eur"),
            (pl.col("QUANTITY_IN_100KG").fill_null(0.0) * 100.0).alias("quantity_kg"),
        ])
        .drop(["VALUE_IN_EUROS", "QUANTITY_IN_100KG"])
        .filter(pl.col("value_eur") > 0)  # Odfiltrowanie pustych przebiegów handlowych
        .sort(["importer_country", "cn_code", "period", "partner_country"])
    )

    out_path = SILVER_DIR / "comext_trade.parquet"
    df_clean.write_parquet(out_path)
    print(f"[Silver] Zapisano dane Comext ({len(df_clean)} wierszy) -> {out_path}")


def run_silver_transformations() -> None:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    clean_nbp()
    clean_macro()
    clean_comext()


if __name__ == "__main__":
    run_silver_transformations()