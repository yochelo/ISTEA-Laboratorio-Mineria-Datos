from math import isclose, isfinite

import pandas as pd


def risk_level(probability):
    if probability >= 0.70:
        return "HIGH"
    if probability >= 0.30:
        return "MEDIUM"
    return "LOW"


def predict_churn(model, customer):
    data = pd.DataFrame([customer.model_dump()])

    prediction = model.predict(data)[0]
    probabilities = [float(value) for value in model.predict_proba(data)[0]]

    yes_index = list(model.classes_).index("Yes")
    if (
        len(probabilities) != len(model.classes_)
        or not all(isfinite(value) and 0 <= value <= 1 for value in probabilities)
        or not isclose(sum(probabilities), 1.0)
    ):
        raise ValueError("Model produced invalid probabilities")
    probability = probabilities[yes_index]

    return {
        "prediction": str(prediction),
        "probability": probability,
        "risk_level": risk_level(probability),
    }
