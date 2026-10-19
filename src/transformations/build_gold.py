import duckdb
import polars as pl
from src.config import SILVER_DIR, GOLD_DIR

COUNTRY_NAMES_PL = {
    "AT": "Austria", "BE": "Belgia", "BG": "Bułgaria", "CY": "Cypr",
    "CZ": "Czechy", "DE": "Niemcy", "DK": "Dania", "EE": "Estonia",
    "EL": "Grecja", "ES": "Hiszpania", "FI": "Finlandia", "FR": "Francja",
    "HR": "Chorwacja", "HU": "Węgry", "IE": "Irlandia", "IT": "Włochy",
    "LT": "Litwa", "LU": "Luksemburg", "LV": "Łotwa", "MT": "Malta",
    "NL": "Holandia", "PT": "Portugalia", "RO": "Rumunia", "SE": "Szwecja",
    "SI": "Słowenia", "SK": "Słowacja"
}


def run_gold_transformations() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    db_path = GOLD_DIR / "analytics.duckdb"

    con = duckdb.connect(str(db_path))

    # 1. Tabela wymiaru krajów (dim_countries)
    df_names = pl.DataFrame({
        "country_code": list(COUNTRY_NAMES_PL.keys()),
        "country_name_pl": list(COUNTRY_NAMES_PL.values()),
    })
    con.register("df_names_view", df_names)

    con.execute(f"""
        CREATE OR REPLACE TABLE dim_countries AS
        WITH latest_macro AS (
            SELECT 
                country_code,
                year,
                population,
                gdp_per_capita_eur,
                ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY year DESC) AS rn
            FROM read_parquet('{SILVER_DIR.as_posix()}/macro_countries.parquet')
        )
        SELECT 
            n.country_code,
            n.country_name_pl,
            m.population,
            m.gdp_per_capita_eur
        FROM df_names_view n
        LEFT JOIN latest_macro m ON n.country_code = m.country_code AND m.rn = 1
        ORDER BY n.country_code;
    """)

    # 2. Tabela faktów miesięcznych (fact_monthly_trade)
    # Łączy import ze świata (WORLD) i z Polski (PL) oraz kursy NBP
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_monthly_trade AS
        WITH world_trade AS (
            SELECT 
                importer_country,
                cn_code,
                period,
                year,
                value_eur AS total_import_eur,
                quantity_kg AS total_import_kg
            FROM read_parquet('{SILVER_DIR.as_posix()}/comext_trade.parquet')
            WHERE partner_country IN ('WORLD', 'TOTAL')
        ),
        pl_trade AS (
            SELECT 
                importer_country,
                cn_code,
                period,
                value_eur AS pl_import_eur,
                quantity_kg AS pl_import_kg
            FROM read_parquet('{SILVER_DIR.as_posix()}/comext_trade.parquet')
            WHERE partner_country = 'PL'
        ),
        nbp AS (
            SELECT period, avg_eur_pln
            FROM read_parquet('{SILVER_DIR.as_posix()}/nbp_monthly.parquet')
        )
        SELECT 
            w.importer_country,
            c.country_name_pl,
            w.cn_code,
            w.period,
            w.year,
            w.total_import_eur,
            w.total_import_kg,
            COALESCE(p.pl_import_eur, 0.0) AS pl_import_eur,
            COALESCE(p.pl_import_kg, 0.0) AS pl_import_kg,
            -- Udział Polski w imporcie danego kraju (%) [ograniczony od góry do 100% na wypadek asymetrii Intrastat]
            LEAST(
                ROUND((COALESCE(p.pl_import_eur, 0.0) / NULLIF(w.total_import_eur, 0)) * 100.0, 2),
                100.0
            ) AS pl_share_pct,
            -- Średnia cena jednostkowa EUR/kg na całym rynku (segment tani vs premium)
            ROUND(w.total_import_eur / NULLIF(w.total_import_kg, 0), 2) AS market_unit_price_eur_kg,
            -- Średnia cena jednostkowa EUR/kg dla mebli z Polski
            ROUND(p.pl_import_eur / NULLIF(p.pl_import_kg, 0), 2) AS pl_unit_price_eur_kg,
            n.avg_eur_pln,
            -- Przychód eksporterów z Polski przeliczony na PLN wg średniego kursu NBP
            ROUND(COALESCE(p.pl_import_eur, 0.0) * n.avg_eur_pln, 2) AS pl_import_pln
        FROM world_trade w
        LEFT JOIN pl_trade p 
            ON w.importer_country = p.importer_country 
            AND w.cn_code = p.cn_code 
            AND w.period = p.period
        LEFT JOIN nbp n 
            ON w.period = n.period
        LEFT JOIN dim_countries c 
            ON w.importer_country = c.country_code
        ORDER BY w.importer_country, w.cn_code, w.period;
    """)

    # 3. Tabela analityczna trendów rocznych (mart_annual_summary)
    con.execute("""
        CREATE OR REPLACE TABLE mart_annual_summary AS
        SELECT 
            f.importer_country,
            f.country_name_pl,
            f.cn_code,
            f.year,
            COUNT(DISTINCT f.period) AS months_reported,
            SUM(f.total_import_eur) AS annual_total_import_eur,
            SUM(f.total_import_kg) AS annual_total_import_kg,
            SUM(f.pl_import_eur) AS annual_pl_import_eur,
            SUM(f.pl_import_pln) AS annual_pl_import_pln,
            LEAST(
                ROUND((SUM(f.pl_import_eur) / NULLIF(SUM(f.total_import_eur), 0)) * 100.0, 2),
                100.0
            ) AS annual_pl_share_pct,
            ROUND(SUM(f.total_import_eur) / NULLIF(SUM(f.total_import_kg), 0), 2) AS annual_market_eur_kg,
            ROUND(AVG(f.avg_eur_pln), 4) AS annual_avg_eur_pln,
            d.population,
            d.gdp_per_capita_eur
        FROM fact_monthly_trade f
        LEFT JOIN dim_countries d ON f.importer_country = d.country_code
        GROUP BY 
            f.importer_country, f.country_name_pl, f.cn_code, f.year,
            d.population, d.gdp_per_capita_eur
        ORDER BY f.importer_country, f.cn_code, f.year;
    """)

    # Eksportujemy tabele również do plików Parquet w katalogu data/gold/
    con.execute(f"COPY dim_countries TO '{GOLD_DIR.as_posix()}/dim_countries.parquet' (FORMAT PARQUET);")
    con.execute(f"COPY fact_monthly_trade TO '{GOLD_DIR.as_posix()}/fact_monthly_trade.parquet' (FORMAT PARQUET);")
    con.execute(f"COPY mart_annual_summary TO '{GOLD_DIR.as_posix()}/mart_annual_summary.parquet' (FORMAT PARQUET);")

    fact_count = con.execute("SELECT COUNT(*) FROM fact_monthly_trade").fetchone()[0]
    mart_count = con.execute("SELECT COUNT(*) FROM mart_annual_summary").fetchone()[0]
    con.close()

    print(f"[Gold] Zbudowano model w DuckDB ({db_path}):")
    print(f"       - fact_monthly_trade: {fact_count} wierszy")
    print(f"       - mart_annual_summary: {mart_count} wierszy")


if __name__ == "__main__":
    run_gold_transformations()