import numpy as np
import pandas as pd
import pytest

from src.evaluation.evaluate import evaluate_model
from src.training.train import select_candidate, split_data, validation_folds


def test_validation_folds_are_reproducible_stratified_and_exclude_holdout():
    data = pd.DataFrame({
        "customerID": range(100),
        "tenure": range(100),
        "Churn": ["No"] * 75 + ["Yes"] * 25,
    })
    X_train, X_test, y_train, y_test = split_data(data, test_size=0.2, random_state=42)
    assert list(X_train.columns) == ["tenure"]
    assert len(X_test) == 20
    assert y_test.value_counts().to_dict() == {"No": 15, "Yes": 5}
    assert set(X_train.index).isdisjoint(X_test.index)

    folds = validation_folds(X_train, y_train, n_splits=5, random_state=42)
    repeated = validation_folds(X_train, y_train, n_splits=5, random_state=42)
    assert len(folds) == 5
    tested = []
    for (fit, validation), (fit_again, validation_again) in zip(folds, repeated):
        np.testing.assert_array_equal(fit, fit_again)
        np.testing.assert_array_equal(validation, validation_again)
        assert set(fit).isdisjoint(validation)
        assert len(fit) + len(validation) == len(X_train)
        assert set(X_train.index[validation]).isdisjoint(X_test.index)
        assert y_train.iloc[validation].value_counts().to_dict() == {"No": 12, "Yes": 4}
        tested.extend(validation)
    assert sorted(tested) == list(range(len(X_train)))


def test_selection_prioritizes_eligibility_then_recall_f1_and_simplicity():
    def candidate(name, precision, recall, f1):
        return {"name": name, "mean": {"precision": precision, "recall": recall, "f1": f1}}

    ineligible = candidate("ineligible", 0.49, 0.95, 0.65)
    lower_recall = candidate("lower_recall", 0.8, 0.4, 0.53)
    lower_f1 = candidate("lower_f1", 0.50, 0.55, 0.52)
    simpler = candidate("simpler", 0.60, 0.55, 0.57)
    complex_model = candidate("complex", 0.60, 0.55, 0.57)
    assert select_candidate([ineligible, lower_recall, lower_f1], 0.50) is lower_f1
    assert select_candidate(
        [ineligible, lower_recall, lower_f1, simpler, complex_model], 0.50
    ) is simpler
    with pytest.raises(ValueError, match="No candidate reached"):
        select_candidate([ineligible], 0.50)


def test_evaluation_uses_yes_probability_and_orders_confusion_matrix():
    class Model:
        classes_ = np.array(["Yes", "No"])

        def predict(self, features):
            return np.array(["No", "Yes", "Yes", "No", "No"])

        def predict_proba(self, features):
            probabilities = np.array([0.1, 0.8, 0.9, 0.4, 0.3])
            return np.column_stack([probabilities, 1 - probabilities])

    labels = pd.Series(["No", "No", "Yes", "Yes", "Yes"])
    metrics = evaluate_model(Model(), pd.DataFrame(index=labels.index), labels)
    assert metrics.pop("confusion_matrix") == [[1, 1], [2, 1]]
    assert metrics == pytest.approx({
        "accuracy": 0.4, "precision": 0.5, "recall": 1 / 3,
        "f1": 0.4, "roc_auc": 2 / 3,
    })
