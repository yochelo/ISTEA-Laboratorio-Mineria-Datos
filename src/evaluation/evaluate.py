from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def score_predictions(actual, predicted, positive_probability):
    return {
        "accuracy": accuracy_score(actual, predicted),
        "precision": precision_score(actual, predicted, pos_label="Yes", zero_division=0),
        "recall": recall_score(actual, predicted, pos_label="Yes", zero_division=0),
        "f1": f1_score(actual, predicted, pos_label="Yes", zero_division=0),
        "roc_auc": roc_auc_score(actual == "Yes", positive_probability),
    }


def confusion_counts(actual, predicted):
    return confusion_matrix(actual, predicted, labels=["No", "Yes"]).tolist()


def positive_probabilities(model, features):
    positive_index = list(model.classes_).index("Yes")
    return model.predict_proba(features)[:, positive_index]


def evaluate_model(model, features, actual):
    predicted = model.predict(features)
    return {
        **score_predictions(actual, predicted, positive_probabilities(model, features)),
        "confusion_matrix": confusion_counts(actual, predicted),
    }
