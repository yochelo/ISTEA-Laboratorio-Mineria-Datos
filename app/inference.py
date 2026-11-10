import pandas as pd


def predict_churn(model, customer):
    # Convertimos los datos recibidos a un DataFrame
    data = pd.DataFrame([customer.model_dump()])

    # El Pipeline aplica el preprocesamiento y predice
    prediction = model.predict(data)[0]

    # Probabilidad correspondiente a Churn = Yes
    probabilities = model.predict_proba(data)[0]
    yes_index = list(model.classes_).index("Yes")
    probability = float(probabilities[yes_index])

    return {
        "prediction": str(prediction),
        "probability": probability
    }