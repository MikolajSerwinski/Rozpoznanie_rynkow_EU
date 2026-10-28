# 🪑 Rozpoznanie rynków eksportowych w UE dla polskiego producenta mebli

Projekt zaliczeniowy z przedmiotu **Inżynieria danych**. Rozwiązanie obejmuje zautomatyzowany, warstwowy potok danych (Data Pipeline) oraz interaktywną aplikację analityczną w **Streamlit**, wspierającą polskiego producenta mebli w wyborze najbardziej perspektywicznych rynków eksportowych w Unii Europejskiej.

---

## 1. Cel biznesowy i pytania odbiorcy

* **Odbiorca:** Polski producent mebli szukający nowych zagranicznych rynków zbytu w Unii Europejskiej.
* **Wspierana decyzja:** Wybór rynków docelowych do ekspansji eksportowej na podstawie dynamiki popytu, pozycji konkurencyjnej polskich eksporterów, segmentacji cenowej (rynek wolumenowy vs premium) oraz ryzyka kursowego.
* **Pytania analityczne (Karta projektu):**
  1. **Które kraje najszybciej zwiększają import mebli w ostatnich 3 latach?**
  2. **Jaki udział w ich imporcie ma Polska i czy ten udział rośnie?**
  3. **Jaka jest średnia cena jednostkowa (EUR/kg), czyli czy dany rynek jest tani (wolumenowy) czy premium?**
  4. **Jak zmiany kursu EUR/PLN wpływają na przychód eksportera przeliczony na PLN?**

---

## 2. Źródła danych i architektura

Potok integruje automatycznie trzy zewnętrzne, publiczne źródła danych:
1. **Eurostat Comext API (`ds-045409`):** Miesięczny import krajów UE według kodów Nomenklatury Scalonej CN (`94` – meble ogółem, `9401` – meble do siedzenia, `9403` – pozostałe meble), kraju partnerskiego (`PL` oraz `WORLD`) z miarami wartości (`VALUE_IN_EUROS`) i masy netto (`QUANTITY_IN_100KG`).
2. **API NBP (Tabela A):** Historyczne i bieżące kursy średnie waluty `EUR/PLN`.
3. **Eurostat Makro API (`tps00001`, `nama_10_pc`):** Kontekst wielkości rynku (liczba ludności) i zamożności konsumentów (PKB per capita w EUR).

### Warstwowe przechowywanie danych (Medallion Architecture):
* **`data/raw/` (Bronze):** Surowe odpowiedzi JSON z API (z obsługą ponawiania zapytań `tenacity`, podziałem na roczne okna dla NBP i ładowaniem przyrostowym dla Comext).
* **`data/silver/` (Clean):** Oczyszczone i ustandaryzowane tabele w formacie kolumnowym **Parquet** (`Polars`) – zdekodowany format JSON-stat 2.0, przeliczona masa ze **100 kg** na **kg** oraz kursy walut zagregowane do średnich miesięcznych.
* **`data/gold/` (Serving):** Lokalna baza analityczna **DuckDB** (`analytics.duckdb`) oraz pliki Parquet realizujące schemat gwiazdy (`dim_countries`, `fact_monthly_trade`, `mart_annual_summary`).

---

## 3. Struktura repozytorium

```text
rozpoznanie-rynkow-eksportowych/
├── .env.example               # Szablon konfiguracji (bez sekretów)
├── pyproject.toml             # Deklaracja zależności Python (uv)
├── uv.lock                    # Zablokowane wersje pakietów gwarantujące powtarzalność
├── README.md                  # Instrukcja uruchomienia i opis projektu
├── PROGRESS.md                # Dziennik postępów (Tydzień 1 – Tydzień 4)
├── docs/                      # Dokumentacja projektowa
│   ├── 01_kontekst_i_perspektywy.md  # Analiza 4 perspektyw (biznesowa, dziedzinowa, techniczna, prawna)
│   ├── 02_architektura.md            # Diagram architektury i przepływu danych
│   ├── 03_slownik_danych.md          # Słownik danych (tabele, kolumny, typy, źródła)
│   ├── 04_rejestr_decyzji_ADR.md     # Rejestr decyzji architektonicznych (ADR)
│   └── 05_ograniczenia_i_rozwoj.md   # Ograniczenia rozwiązania i kierunki rozwoju
├── src/                       # Kod źródłowy potoku danych
│   ├── config.py              # Konfiguracja ścieżek, lat i kodów CN
│   ├── run_pipeline.py        # Główny skrypt orkiestrujący (Ingestion -> Silver -> Gold -> Testy)
│   ├── ingestion/             # Pobieranie danych z API (Comext, NBP, Eurostat Makro)
│   └── transformations/       # Czyszczenie (Polars) i budowa modelu analitycznego (DuckDB)
├── tests/                     # Automatyczne testy jakości danych i testy jednostkowe (pytest)
│   ├── test_data_quality.py          # 6 testów jakości danych warstwy Gold
│   └── test_unit_transformations.py  # Testy jednostkowe parsera JSON-stat
└── app/                       # Aplikacja analityczna
    └── dashboard.py           # Interaktywny dashboard w Streamlit + Plotly
```
---

## 4. Instrukcja instalacji i uruchomienia krok po kroku

### Wymagania wstępne
* Zainstalowany **Python 3.11+** oraz menedżer pakietów **[uv](https://docs.astral.sh/uv/)**.
* Dostęp do internetu (wymagany przy pierwszym uruchomieniu potoku w celu pobrania danych z API Eurostatu i NBP).

### A. Instrukcja dla systemu Windows (PowerShell / CMD)

1. **Sklonuj repozytorium i przejdź do katalogu projektu:**
   ```powershell
   git clone <ADRES_TWOJEGO_REPOZYTORIUM>
   cd rozpoznanie-rynkow-eksportowych
   ```
2. **Utwórz plik konfiguracyjny `.env` na podstawie szablonu:**
   ```powershell
   copy .env.example .env
   ```
3. **Zainstaluj zależności z pliku `uv.lock`:**
   ```powershell
   uv sync
   ```
4. **Uruchom potok danych oraz automatyczne testy jakości (`pytest`):**
   ```powershell
   uv run python -m src.run_pipeline
   ```
5. **Uruchom aplikację analityczną Streamlit:**
   ```powershell
   uv run streamlit run app/dashboard.py
   ```
   *(Aplikacja otworzy się automatycznie w przeglądarce pod adresem `http://localhost:8501`)*

### B. Instrukcja dla systemów Linux oraz macOS (Bash / Zsh)

1. **Sklonuj repozytorium i przejdź do katalogu projektu:**
   ```bash
   git clone <ADRES_TWOJEGO_REPOZYTORIUM>
   cd rozpoznanie-rynkow-eksportowych
   ```
2. **Utwórz plik konfiguracyjny `.env` na podstawie szablonu:**
   ```bash
   cp .env.example .env
   ```
3. **Zainstaluj zależności z pliku `uv.lock`:**
   ```bash
   uv sync
   ```
4. **Uruchom potok danych oraz automatyczne testy jakości (`pytest`):**
   ```bash
   uv run python -m src.run_pipeline
   ```
5. **Uruchom aplikację analityczną Streamlit:**
   ```bash
   uv run streamlit run app/dashboard.py
   ```
   *(Aplikacja otworzy się automatycznie w przeglądarce pod adresem `http://localhost:8501`)*