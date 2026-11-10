import joblib


def load_model():
    return joblib.load("models/churn_model.joblib")