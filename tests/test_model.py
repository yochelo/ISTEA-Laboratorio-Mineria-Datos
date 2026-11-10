import joblib

from src.data.load_data import load_data


def test_model_prediction():
    model = joblib.load("models/churn_model.joblib")

    df = load_data("data/raw/customer_churn_historical.csv")
    X = df.drop(columns=["customerID", "Churn"])

    predictions = model.predict(X.head(5))

    assert len(predictions) == 5
    assert set(predictions).issubset({"Yes", "No"})