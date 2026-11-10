
import pandas as pd


MODEL_VERSION = "1"


def predict_churn(model, customer):
    data = pd.DataFrame([customer.model_dump()])

    prediction = model.predict(data)[0]
    probabilities = model.predict_proba(data)[0]

    yes_index = list(model.classes_).index("Yes")
    probability = float(probabilities[yes_index])

    if probability < 0.30:
        risk_level = "LOW"
    elif probability < 0.70:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return {
        "prediction": str(prediction),
        "probability": probability,
        "risk_level": risk_level,
        "model_version": MODEL_VERSION
    }
