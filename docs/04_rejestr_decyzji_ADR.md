# Rejestr decyzji architektonicznych (ADR)

## ADR-01: Wybór silnika przetwarzania i przechowywania danych (DuckDB + Polars + Parquet)
* **Wybór:** Lokalne pliki Parquet przetwarzane za pomocą Polars i DuckDB.
* **Rozważane alternatywy:** Relacyjna baza PostgreSQL uruchamiana w Dockerze; czysty `pandas` z plikami CSV.
* **Uzasadnienie:** Dane z Comext mają charakter wybitnie analityczny (OLAP). Format Parquet zapewnia kompresję i zachowanie typów danych, a DuckDB/Polars pozwalają na natychmiastowe wykonywanie zapytań bez narzutu związanego z konfiguracją serwera bazodanowego, co zwiększa powtarzalność projektu na innym komputerze.

## ADR-02: Wybór kodów CN do analizy
* **Wybór:** Pobieranie agregatu działu `94` (Meble ogółem) oraz dwóch kluczowych grup 4-cyfrowych: `9401` (meble do siedzenia) i `9403` (pozostałe meble).
* **Rozważane alternatywy:** Pobieranie wszystkich 8-cyfrowych kodów CN z działu 94.
* **Uzasadnienie:** Pobieranie kilkuset 8-cyfrowych kodów CN dla 27 krajów w ujęciu miesięcznym przekracza limity pojedynczych zapytań API Eurostatu i nie wnosi dodatkowej wartości na etapie strategicznego wyboru kraju eksportu. Agregat `94` oraz podział na `9401` i `9403` idealnie odpowiadają na pytania odbiorcy.