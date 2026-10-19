```markdown
# Słownik danych (Data Dictionary)

## 1. Warstwa Gold (`data/gold/analytics.duckdb`)

### Tabela: `dim_countries` (Wymiar krajów UE)
| Kolumna | Typ danych | Znaczenie biznesowe | Źródło |
| :--- | :--- | :--- | :--- |
| `country_code` | `VARCHAR` (PK) | Dwuliterowy kod kraju importera wg Eurostatu (np. `DE`, `FR`, `EL`) | Eurostat |
| `country_name_pl` | `VARCHAR` | Polska nazwa kraju (np. Niemcy, Francja, Grecja) | Słownik wewnętrzny |
| `population` | `BIGINT` | Liczba ludności kraju (wielkość rynku konsumenckiego) | Eurostat (`tps00001`) |
| `gdp_per_capita_eur` | `DOUBLE` | PKB per capita w cenach bieżących w EUR (zamożność rynku) | Eurostat (`nama_10_pc`) |

### Tabela: `fact_monthly_trade` (Miesięczna tabela faktów importu mebli)
| Kolumna | Typ danych | Znaczenie biznesowe | Źródło / Wyliczenie |
| :--- | :--- | :--- | :--- |
| `importer_country` | `VARCHAR` (FK) | Kod kraju UE importującego meble | Comext (`ds-045409`) |
| `country_name_pl` | `VARCHAR` | Polska nazwa kraju importera | `dim_countries` |
| `cn_code` | `VARCHAR` | Kod Nomenklatury Scalonej (`94` – meble ogółem, `9401` – do siedzenia, `9403` – pozostałe) | Comext (`ds-045409`) |
| `period` | `VARCHAR` | Miesiąc sprawozdawczy w formacie `YYYY-MM` | Comext (`ds-045409`) |
| `year` | `INTEGER` | Rok sprawozdawczy | Wyliczone z `period` |
| `total_import_eur` | `DOUBLE` | Całkowita wartość importu mebli przez dany kraj ze świata (w EUR) | Comext (`partner=WORLD`) |
| `total_import_kg` | `DOUBLE` | Całkowita masa importu mebli ze świata (w kg, po przeliczeniu ze 100 kg) | Comext (`QUANTITY_IN_100KG * 100`) |
| `pl_import_eur` | `DOUBLE` | Wartość importu mebli przez dany kraj z Polski (w EUR) | Comext (`partner=PL`) |
| `pl_import_kg` | `DOUBLE` | Masa importu mebli z Polski (w kg) | Comext (`partner=PL`) |
| `pl_share_pct` | `DOUBLE` | Udział Polski w całkowitym imporcie mebli danego kraju (w %) | `(pl_import_eur / total_import_eur) * 100` |
| `market_unit_price_eur_kg` | `DOUBLE` | Średnia cena jednostkowa 1 kg importowanych mebli na rynku (EUR/kg – wskaźnik segmentu tani vs premium) | `total_import_eur / total_import_kg` |
| `pl_unit_price_eur_kg` | `DOUBLE` | Średnia cena jednostkowa 1 kg mebli importowanych z Polski (EUR/kg) | `pl_import_eur / pl_import_kg` |
| `avg_eur_pln` | `DOUBLE` | Średni miesięczny kurs EUR/PLN | API NBP (Tabela A) |
| `pl_import_pln` | `DOUBLE` | Wartość polskiego eksportu do danego kraju wyrażona w PLN | `pl_import_eur * avg_eur_pln` |

### Tabela: `mart_annual_summary` (Roczne podsumowanie rynków eksportowych)
| Kolumna | Typ danych | Znaczenie biznesowe | Źródło / Wyliczenie |
| :--- | :--- | :--- | :--- |
| `importer_country` | `VARCHAR` | Kod kraju importera | `fact_monthly_trade` |
| `cn_code` | `VARCHAR` | Kod CN grupy mebli | `fact_monthly_trade` |
| `year` | `INTEGER` | Rok analizy | `fact_monthly_trade` |
| `months_reported` | `BIGINT` | Liczba zaraportowanych miesięcy w danym roku (do kontroli pełnych lat) | `COUNT(DISTINCT period)` |
| `annual_total_import_eur` | `DOUBLE` | Roczna wartość importu mebli ze świata (EUR) | `SUM(total_import_eur)` |
| `annual_pl_import_eur` | `DOUBLE` | Roczna wartość importu mebli z Polski (EUR) | `SUM(pl_import_eur)` |
| `annual_pl_share_pct` | `DOUBLE` | Średni roczny udział Polski w imporcie danego kraju (%) | `(SUM(pl_import_eur) / SUM(total_import_eur)) * 100` |
| `annual_market_eur_kg` | `DOUBLE` | Średnia roczna cena jednostkowa na rynku (EUR/kg) | `SUM(total_import_eur) / SUM(total_import_kg)` |