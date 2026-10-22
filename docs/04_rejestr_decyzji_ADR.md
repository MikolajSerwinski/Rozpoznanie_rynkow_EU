# Rejestr decyzji architektonicznych (ADR)

## ADR-01: Wybór silnika przetwarzania i przechowywania danych (DuckDB + Polars + Parquet)
* **Wybór:** Lokalne pliki Parquet przetwarzane za pomocą Polars i DuckDB.
* **Rozważane alternatywy:** Relacyjna baza PostgreSQL uruchamiana w Dockerze; czysty `pandas` z plikami CSV.
* **Uzasadnienie:** Dane z Comext mają charakter wybitnie analityczny (OLAP). Format Parquet zapewnia kompresję i zachowanie typów danych, a DuckDB/Polars pozwalają na natychmiastowe wykonywanie zapytań bez narzutu związanego z konfiguracją serwera bazodanowego, co zwiększa powtarzalność projektu na innym komputerze.

## ADR-02: Wybór kodów CN do analizy
* **Wybór:** Pobieranie agregatu działu `94` (Meble ogółem) oraz dwóch kluczowych grup 4-cyfrowych: `9401` (meble do siedzenia) i `9403` (pozostałe meble).
* **Rozważane alternatywy:** Pobieranie wszystkich 8-cyfrowych kodów CN z działu 94.
* **Uzasadnienie:** Pobieranie kilkuset 8-cyfrowych kodów CN dla 27 krajów w ujęciu miesięcznym przekracza limity pojedynczych zapytań API Eurostatu i nie wnosi dodatkowej wartości na etapie strategicznego wyboru kraju eksportu. Agregat `94` oraz podział na `9401` i `9403` idealnie odpowiadają na pytania odbiorcy.

## ADR-03: Sposób obliczania dynamiki 3-letniej przy niepełnym roku bieżącym
* **Wybór:** Obliczanie dynamiki wzrostu importu na bazie **średniego miesięcznego importu w danym roku** (`annual_total_import_eur / months_reported`).
* **Rozważane alternatywy:** Porównywanie bezwzględnych sum rocznych (`SUM(total_import_eur)`) lub sztywne odrzucenie bieżącego roku z analizy.
* **Uzasadnienie:** Ze względu na ok. 2-miesięczne opóźnienie publikacji w Eurostat Comext, najnowszy rok ma mniejszą liczbę zaraportowanych miesięcy niż lata historyczne. Porównanie sum rocznych wykazałoby pozorny spadek importu w ostatnim roku, natomiast całkowite odrzucenie bieżącego roku pozbawiłoby odbiorcę najnowszych trendów. Normalizacja przez liczbę zaraportowanych miesięcy (`months_reported`) pozwala na rzetelne porównanie tempa importu.

## ADR-04: Wybór technologii aplikacji końcowej (Streamlit + Plotly)
* **Wybór:** Aplikacja webowa w `Streamlit` z interaktywnymi wykresami `Plotly` odczytująca dane w trybie `read_only=True` z lokalnej bazy `DuckDB`.
* **Rozważane alternatywy:** Raport w Power BI Desktop (`.pbix`); aplikacja we Flask/FastAPI + React.
* **Uzasadnienie:** Power BI Desktop wymaga systemu Windows i nie jest w pełni multiplatformowy, co utrudniłoby ocenę projektu na macOS/Linux. Streamlit działa w 100% w tym samym środowisku Python (`uv`), pozwala na łatwą budowę symulatora walutowego (analiza scenariuszy kursu EUR/PLN) oraz bezpośrednie wyzwolenie potoku ETL przyciskiem w interfejsie.