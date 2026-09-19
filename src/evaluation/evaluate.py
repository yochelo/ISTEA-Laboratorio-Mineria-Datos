
# Funciones para la evaluación de los modelos.

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)

def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(
            y_test, y_pred, pos_label="Yes", zero_division=0
        ),
        "recall": recall_score(
            y_test, y_pred, pos_label="Yes", zero_division=0
        ),
        "f1": f1_score(
            y_test, y_pred, pos_label="Yes", zero_division=0
        )
    }

    return metrics
