# Architektura rozwiązania i przepływ danych

## 1. Diagram przepływu danych (Architektura Medallion)

```mermaid
flowchart LR
    subgraph Zrodla["Zewnętrzne źródła danych (API)"]
        A1["Eurostat Comext API\n(ds-045409: Import CN 94)"]
        A2["API NBP\n(Kursy średnie EUR/PLN)"]
        A3["Eurostat Makro API\n(PKB nama_10_pc, Ludność tps00001)"]
    end

    subgraph Raw["Warstwa Raw / Bronze (JSON)"]
        B1["data/raw/comext/*.json"]
        B2["data/raw/nbp/*.json"]
        B3["data/raw/eurostat_macro/*.json"]
    end

    subgraph Silver["Warstwa Clean / Silver (Parquet)"]
        S1["comext_trade.parquet\n(Rozpakowanie JSON-stat, 100kg -> kg)"]
        S2["nbp_monthly.parquet\n(Agregacja do średnich miesięcznych)"]
        S3["macro_countries.parquet\n(Czyszczenie i forward-fill)"]
    end

    subgraph Gold["Warstwa Serving / Gold (DuckDB + Parquet)"]
        G1[("analytics.duckdb\n- dim_countries\n- fact_monthly_trade\n- mart_annual_summary")]
    end

    subgraph Jakość["Kontrola Jakości"]
        T1["pytest (6 testów jakości:\nkompletność, unikalność, referencje,\ndozwolone wartości, zakresy, reguły dziedzinowe)"]
    end

    subgraph App["Warstwa Prezentacji"]
        UI["Aplikacja Streamlit\n(4 widoki biznesowe dla producenta mebli)"]
    end

    A1 --> B1 --> S1 --> G1
    A2 --> B2 --> S2 --> G1
    A3 --> B3 --> S3 --> G1
    G1 --> T1
    G1 --> UI