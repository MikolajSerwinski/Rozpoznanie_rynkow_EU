# Kontekst projektu i analiza 4 perspektyw

## 1. Odbiorca i problem biznesowy (Perspektywa biznesowa)
* **Odbiorca:** Polski średni/duży producent mebli planujący dywersyfikację sprzedaży i wejście na nowe rynki zagraniczne w Unii Europejskiej.
* **Wspierana decyzja:** Wybór 2–3 najbardziej perspektywicznych rynków eksportowych w UE pod kątem dynamiki popytu, obecnej konkurencji z Polski, pozycjonowania cenowego (segment ekonomiczny vs premium) oraz ryzyka walutowego.
* **Pytania odbiorcy (Karta projektu):**
  1. Które kraje UE najszybciej zwiększają import mebli w ostatnich 3 latach?
  2. Jaki udział w ich imporcie ma Polska i czy ten udział rośnie?
  3. Jaka jest średnia cena jednostkowa (EUR/kg), czyli czy dany kraj to rynek tani (wolumenowy) czy premium?
  4. Jak zmiany kursu EUR/PLN wpływają na przychód eksportera przeliczony na PLN?
* **Pomiar wartości i koszty utrzymania:** Wartość biznesowa to skrócenie czasu analizy rynkowej z kilku dni ręcznego pobierania tabel z Eurostatu do kilku minut w interaktywnym dashboardzie. Koszt utrzymania rozwiązania jest zerowy (darmowe API publiczne, lokalny silnik DuckDB/Polars, otwarte narzędzia).

## 2. Perspektywa dziedzinowa (Statystyka handlu zagranicznego i kody CN)
* **Nomenklatura Scalona (CN – Combined Nomenclature):** Towary w handlu międzynarodowym UE są klasyfikowane za pomocą kodów CN. Dział **94** obejmuje meble (w tym `9401` – meble do siedzenia oraz `9403` – pozostałe meble drewniane, metalowe i biurowe).
* **Specyfika miar w Eurostat Comext:** Wartość handlu raportowana jest w EUR (`VALUE_IN_EUROS`), natomiast masa netto w jednostkach **100 kg** (`QUANTITY_IN_100KG`). Wyliczenie wskaźnika ceny jednostkowej (EUR/kg) wymaga przemnożenia wskaźnika masy przez 100 w warstwie czyszczącej (*Silver*).
* **Ograniczenia dziedzinowe:** Statystyki wewnątrzunijne (Intrastat) posiadają progi asymetrii i opóźnienie publikacji ok. 6–8 tygodni po zakończeniu miesiąca sprawozdawczego.

## 3. Perspektywa techniczna
* Zastosowano architekturę warstwową **Medallion** (`raw` -> `silver` -> `gold`) opartą o Python (`uv`), bibliotekę `Polars` oraz bazę `DuckDB` z zapisem kolumnowym `Parquet`.
* Przy 100-krotnie większym wolumenie danych (np. pełna szczegółowość wszystkich 8-cyfrowych kodów CN dla wszystkich krajów świata od 1988 roku) lokalne przetwarzanie zastąpiono by magazynem obiektowym w chmurze (S3/GCS), formatem tabelarycznym Apache Iceberg/Delta Lake oraz rozproszonym silnikiem obliczeniowym (Apache Spark lub chmurowy DuckDB/MotherDuck).

## 4. Perspektywa prawna i etyczna
* Wszystkie wykorzystywane dane (Eurostat Comext, Eurostat Makro, API NBP) to publiczne dane statystyczne udostępniane na otwartych licencjach (dozwolony użytek komercyjny i edukacyjny pod warunkiem wskazania źródła).
* Zbiory zawierają wyłącznie dane zagregowane na poziomie państw i grup towarowych – **całkowity brak danych osobowych (RODO nie ma zastosowania)**.
* **Ryzyko błędnej interpretacji:** Średnia cena za kilogram (EUR/kg) jest miarą przybliżoną – zależy od struktury asortymentowej (np. meble tapicerowane vs ciężkie meble z płyt wiórowych). W aplikacji dodano możliwość filtrowania konkretnych podkategorii CN (`9401` vs `9403`).