# Ograniczenia rozwiązania i możliwe kierunki rozwoju

## 1. Ograniczenia obecnego rozwiązania

### A. Ograniczenia dziedzinowe i źródłowe (Dane)
1. **Opóźnienie publikacji danych w Eurostat Comext:** Miesięczne statystyki handlu międzynarodowego są publikowane z opóźnieniem ok. 6–8 tygodni po zakończeniu miesiąca sprawozdawczego. Oznacza to, że bieżący rok w bazie jest niepełny (rozwiązano to w aplikacji poprzez obliczanie dynamiki ze średnich miesięcznych w danym roku).
2. **Progi asymetrii w systemie Intrastat:** Handel wewnątrzunijny raportowany jest przez firmy przekraczające określone progi statystyczne w danym kraju członkowskim. Może to powodować drobne rozbieżności między eksportem deklarowanym przez Polskę a importem deklarowanym przez kraj partnerski.
3. **Agregacja cenowa (wskaźnik EUR/kg):** Średnia cena za kilogram (`market_unit_price_eur_kg`) na poziomie 2- lub 4-cyfrowego kodu CN zależy nie tylko od zamożności rynku, ale również od struktury surowcowej (np. lekkie meble rattanowe/tapicerowane mają wyższą cenę za kg niż ciężkie meble ze stali lub płyty wiórowej).
4. **Brak kosztów logistyki i ceł poza UE:** Analiza skupia się na rynku wewnętrznym UE (brak barier celnych), ale nie uwzględnia kosztów transportu drogowego (frachtu), które rosną wraz z odległością od granic Polski (np. Hiszpania/Portugalia vs Czechy/Niemcy).

### B. Ograniczenia techniczne
1. **Lokalne przechowywanie danych:** Baza DuckDB i pliki Parquet są przechowywane na lokalnym dysku twardym, co wymaga uruchomienia skryptu `run_pipeline.py` na maszynie użytkownika lub serwerze hostującym aplikację.
2. **Brak harmonogramu w chmurze (Scheduler):** Odświeżanie danych wywoływane jest z wiersza poleceń lub przyciskiem w aplikacji Streamlit, a nie przez całodobowy serwer orkiestracji (np. Airflow / GitHub Actions Cron).

## 2. Możliwe kierunki rozwoju
1. **Wzbogacenie o koszty transportu (API odległości / stawek frachtu):** Dodanie średniego kosztu transportu ciężarowego FTL z centralnej Polski do stolicy danego kraju UE w celu wyliczenia marży netto po kosztach logistyki.
2. **Zejście do poziomu 8-cyfrowych kodów CN (CN8):** Umożliwienie producentowi analizy bardzo wąskich nisz produktowych (np. `9401 61 00` – meble do siedzenia tapicerowane z ramą drewnianą).
3. **Automatyczny harmonogram w GitHub Actions:** Dodanie workflow CI/CD uruchamiającego potok automatycznie 15. dnia każdego miesiąca (po publikacji nowego miesiąca w Comext) i wysyłającego alert mailowy o zmianach trendów.
4. **Prognozowanie szeregów czasowych (ML):** Dodanie modelu sezonowego (np. Prophet / SARIMA) prognozującego popyt na meble w kolejnych dwóch kwartałach.