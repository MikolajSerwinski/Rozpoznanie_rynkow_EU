import polars as pl
from src.transformations.clean_silver import parse_jsonstat


def test_unit_parse_jsonstat_dict_values():
    """Test jednostkowy: poprawne dekodowanie spłaszczonego słownika JSON-stat 2.0 do tabeli Polars."""
    mock_jsonstat = {
        "id": ["reporter", "partner", "time"],
        "size": [2, 1, 2],
        "dimension": {
            "reporter": {"category": {"index": {"DE": 0, "FR": 1}}},
            "partner": {"category": {"index": {"PL": 0}}},
            "time": {"category": {"index": {"2024-01": 0, "2024-02": 1}}},
        },
        "value": {
            "0": 1500.0,  # DE, PL, 2024-01
            "1": 2000.0,  # DE, PL, 2024-02
            "3": 3200.5,  # FR, PL, 2024-02 (indeks 2 jest pusty / brak handlu)
        },
    }

    df = parse_jsonstat(mock_jsonstat)

    assert isinstance(df, pl.DataFrame)
    assert len(df) == 3
    assert set(df.columns) == {"reporter", "partner", "time", "value"}

    fr_row = df.filter((pl.col("reporter") == "FR") & (pl.col("time") == "2024-02"))
    assert len(fr_row) == 1
    assert fr_row["value"][0] == 3200.5


def test_unit_parse_jsonstat_empty_payload():
    """Test jednostkowy: bezpieczna obsługa pustej odpowiedzi z API Eurostatu."""
    empty_jsonstat = {"id": [], "size": [], "value": {}, "dimension": {}}
    df = parse_jsonstat(empty_jsonstat)
    assert df.is_empty()