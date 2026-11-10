from src.data.load_data import load_data


def test_load_data():
    df = load_data("data/raw/customer_churn_historical.csv")

    assert not df.empty
    assert "Churn" in df.columns
    assert "customerID" in df.columns
    assert len(df) == 7043