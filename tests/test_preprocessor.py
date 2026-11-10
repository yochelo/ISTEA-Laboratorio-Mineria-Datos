from src.data.load_data import load_data
from src.features.build_preprocessor import build_preprocessor


def test_preprocessor():
    df = load_data("data/raw/customer_churn_historical.csv")
    X = df.drop(columns=["customerID", "Churn"])

    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)

    assert X_transformed.shape[0] == len(X)
    assert X_transformed.shape[1] > X.shape[1]