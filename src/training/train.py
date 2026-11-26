import hashlib
import json
import subprocess
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import yaml
from mlflow.models import infer_signature
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

from src.data.load_data import load_data
from src.evaluation.evaluate import (
    confusion_counts,
    evaluate_model,
    positive_probabilities,
    score_predictions,
)
from src.features.build_preprocessor import build_preprocessor


def split_data(df, test_size, random_state):
    return train_test_split(
        df.drop(columns=["customerID", "Churn"]),
        df["Churn"],
        test_size=test_size,
        random_state=random_state,
        stratify=df["Churn"],
    )


def validation_folds(features, labels, n_splits, random_state):
    return list(
        StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        .split(features, labels)
    )


def select_candidate(results, min_precision):
    eligible = [result for result in results if result["mean"]["precision"] >= min_precision]
    if not eligible:
        raise ValueError(f"No candidate reached mean precision {min_precision:.2f}")
    # Configuration order breaks exact ties, from simplest to most complex.
    return max(eligible, key=lambda result: (result["mean"]["recall"], result["mean"]["f1"]))


def validate_candidate(pipeline, features, labels, folds, name):
    out_of_fold = np.empty(len(labels), dtype=object)
    scores = []
    for fold, (fit_indices, validation_indices) in enumerate(folds, start=1):
        X_validation = features.iloc[validation_indices]
        y_validation = labels.iloc[validation_indices]
        fitted = clone(pipeline).fit(features.iloc[fit_indices], labels.iloc[fit_indices])
        predicted = fitted.predict(X_validation)
        out_of_fold[validation_indices] = predicted
        metrics = score_predictions(
            y_validation, predicted, positive_probabilities(fitted, X_validation)
        )
        scores.append(metrics)
        mlflow.log_metrics({f"fold_{key}": value for key, value in metrics.items()}, step=fold)
        print(f"{name}: fold {fold}/{len(folds)} complete", flush=True)

    return {
        "folds": scores,
        "mean": {key: float(np.mean([row[key] for row in scores])) for key in scores[0]},
        "std": {key: float(np.std([row[key] for row in scores])) for key in scores[0]},
        "confusion_matrix": confusion_counts(labels, out_of_fold),
    }


def main():
    params = yaml.safe_load(Path("params.yaml").read_text())
    dataset_path = Path("data/raw/customer_churn_historical.csv")
    data = load_data(dataset_path)
    X_train, X_test, y_train, y_test = split_data(data, **params["split"])
    folds = validation_folds(X_train, y_train, **params["validation"])
    classifiers = {
        "dummy": DummyClassifier,
        "logistic_regression": LogisticRegression,
        "random_forest": RandomForestClassifier,
    }
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    source_diff = subprocess.check_output(
        ["git", "diff", "HEAD", "--", "src", "params.yaml", "dvc.yaml", "requirements.txt"],
        encoding="utf-8",
    )
    provenance = {
        "code.base_commit": commit,
        "code.training_files_modified": str(bool(source_diff)).lower(),
        "data.sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    }
    dataset = mlflow.data.from_pandas(data, source=str(dataset_path), name="churn_historical", targets="Churn")
    split_params = {
        "test_size": params["split"]["test_size"],
        "split_seed": params["split"]["random_state"],
        "cv_folds": params["validation"]["n_splits"],
        "cv_seed": params["validation"]["random_state"],
        "min_precision": params["selection"]["min_precision"],
        "positive_label": "Yes",
    }
    mlflow.set_experiment("ISTEA_Churn")
    results = []
    pipelines = {}
    for index, candidate in enumerate(params["candidates"], start=1):
        name = candidate["name"]
        classifier = classifiers[candidate["family"]](**candidate["parameters"])
        pipeline = Pipeline([("preprocessor", build_preprocessor()), ("classifier", classifier)])
        pipelines[name] = pipeline
        print(f"Candidate {index}/{len(params['candidates'])}: {name}", flush=True)
        with mlflow.start_run(run_name=name, tags={**provenance, "phase": "validation"}) as run:
            mlflow.log_input(dataset, context="source")
            mlflow.log_params({**split_params, **classifier.get_params()})
            result = validate_candidate(pipeline, X_train, y_train, folds, name)
            mlflow.log_metrics({f"cv_mean_{key}": value for key, value in result["mean"].items()})
            mlflow.log_metrics({f"cv_std_{key}": value for key, value in result["std"].items()})
            mlflow.log_dict(result, "validation.json")
            results.append({**result, "name": name, "run_id": run.info.run_id})

    winner = select_candidate(results, params["selection"]["min_precision"])
    print(f"Selected {winner['name']}. Fitting on all training observations.", flush=True)
    with mlflow.start_run(run_name=f"Final - {winner['name']}", tags={
        **provenance, "phase": "final", "validation_run_id": winner["run_id"],
    }):
        model = pipelines[winner["name"]].fit(X_train, y_train)
        report = evaluate_model(model, X_test, y_test)
        matrix = report.pop("confusion_matrix")
        mlflow.log_input(dataset, context="source")
        mlflow.log_params({**split_params, **model.named_steps["classifier"].get_params()})
        mlflow.log_metrics(report)
        mlflow.log_dict({"labels": ["No", "Yes"], "matrix": matrix}, "holdout_confusion_matrix.json")
        if source_diff:
            mlflow.log_text(source_diff, "training_source.diff")

        model_path = Path("models/churn_model.joblib")
        joblib.dump(model, model_path)
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        mlflow.set_tag("model.joblib_sha256", digest)
        sample = X_train.head()
        mlflow.sklearn.log_model(
            model,
            name="churn_pipeline",
            signature=infer_signature(sample, model.predict(sample)),
            serialization_format="skops",
            skops_trusted_types=["numpy.dtype"],
            extra_files=[str(model_path)],
        )
        report.update({
            "true_negatives": matrix[0][0], "false_positives": matrix[0][1],
            "false_negatives": matrix[1][0], "true_positives": matrix[1][1],
        })
        Path("reports/metrics.json").write_text(json.dumps(report, indent=4) + "\n")
        print("Final model and holdout metrics saved.", flush=True)


if __name__ == "__main__":
    main()
