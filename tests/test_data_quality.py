import duckdb
import pytest
from src.config import GOLD_DIR, CN_CODES

DB_PATH = GOLD_DIR / "analytics.duckdb"


@pytest.fixture(scope="module")
def db_con():
    if not DB_PATH.exists():
        pytest.fail(f"Baza danych warstwy Gold nie istnieje: {DB_PATH}. Uruchom najpierw potok!")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


def test_1_completeness_no_nulls_in_keys(db_con):
    """Reguła 1 (Kompletność): Kluczowe kolumny w fact_monthly_trade nie mogą zawierać NULL."""
    null_count = db_con.execute("""
        SELECT COUNT(*) 
        FROM fact_monthly_trade
        WHERE importer_country IS NULL 
           OR cn_code IS NULL 
           OR period IS NULL 
           OR total_import_eur IS NULL
    """).fetchone()[0]
    assert null_count == 0, f"Błąd kompletności: znaleziono {null_count} wierszy z wartością NULL w kluczach!"


def test_2_uniqueness_primary_key(db_con):
    """Reguła 2 (Unikalność): Brak duplikatów dla klucza (importer_country, cn_code, period)."""
    dup_count = db_con.execute("""
        SELECT COUNT(*) FROM (
            SELECT importer_country, cn_code, period, COUNT(*) AS cnt
            FROM fact_monthly_trade
            GROUP BY importer_country, cn_code, period
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    assert dup_count == 0, f"Błąd unikalności: znaleziono {dup_count} zduplikowanych kluczy w fact_monthly_trade!"


def test_3_referential_integrity_countries(db_con):
    """Reguła 3 (Integralność referencyjna): Wszystkie kraje z tabeli faktów istnieją w dim_countries."""
    orphan_countries = db_con.execute("""
        SELECT DISTINCT f.importer_country
        FROM fact_monthly_trade f
        LEFT JOIN dim_countries d ON f.importer_country = d.country_code
        WHERE d.country_code IS NULL
    """).fetchall()
    assert len(orphan_countries) == 0, f"Błąd integralności referencyjnej! Brakujące kraje w wymiarze: {orphan_countries}"


def test_4_allowed_values_cn_codes(db_con):
    """Reguła 4 (Dozwolone wartości): Kolumna cn_code zawiera tylko zadeklarowane kody mebli."""
    allowed = [c.strip() for c in CN_CODES]
    actual_codes = [
        row[0] for row in db_con.execute("SELECT DISTINCT cn_code FROM fact_monthly_trade").fetchall()
    ]
    invalid_codes = [c for c in actual_codes if c not in allowed]
    assert len(invalid_codes) == 0, f"Błąd dozwolonych wartości! Nieznane kody CN: {invalid_codes}"


def test_5_range_exchange_rate_eur_pln(db_con):
    """Reguła 5 (Zakresy): Kurs średni EUR/PLN mieści się w realistycznym przedziale 3.50 - 5.50 PLN."""
    out_of_range = db_con.execute("""
        SELECT COUNT(*) 
        FROM fact_monthly_trade
        WHERE avg_eur_pln IS NOT NULL 
          AND (avg_eur_pln < 3.50 OR avg_eur_pln > 5.50)
    """).fetchone()[0]
    assert out_of_range == 0, f"Błąd zakresu: znaleziono {out_of_range} rekordów z kursem EUR/PLN poza przedziałem [3.50, 5.50]!"


def test_6_domain_rules_share_and_positive_trade(db_con):
    """Reguła 6 (Reguła dziedzinowa): Udział Polski w przedziale 0-100%, a import całkowity > 0."""
    invalid_rows = db_con.execute("""
        SELECT COUNT(*)
        FROM fact_monthly_trade
        WHERE pl_share_pct < 0.0 
           OR pl_share_pct > 100.0 
           OR total_import_eur <= 0.0
    """).fetchone()[0]
    assert invalid_rows == 0, f"Błąd reguły dziedzinowej: {invalid_rows} wierszy ma nieprawidłowy udział % lub wartość <= 0!"