import hashlib
import json
from pathlib import Path

import evidently
import pandas as pd
import yaml
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
from evidently.report import Report
from sklearn.model_selection import train_test_split

from src.features.build_preprocessor import categorical_features, numeric_features


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = Path("data/raw/customer_churn_historical.csv")
CURRENT = Path("data/production/customer_churn_current.csv")
FEATURES = numeric_features + categorical_features


def load_windows(root, split):
    historical = pd.read_csv(root / HISTORICAL)
    current = pd.read_csv(root / CURRENT)
    if set(current.columns) != {"customerID", *FEATURES}:
        raise ValueError("Unexpected columns in the production window")

    # Reuse the training split policy without importing its MLflow runtime.
    reference, _, _, _ = train_test_split(
        historical[FEATURES],
        historical["Churn"],
        stratify=historical["Churn"],
        **split,
    )
    if len(reference) != 5634 or len(current) != 2500:
        raise ValueError("Unexpected row counts in the monitoring windows")
    return reference, current[FEATURES]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    split = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))["split"]
    reference, current = load_windows(ROOT, split)
    model = json.loads((ROOT / "app/model_manifest.json").read_text(encoding="utf-8"))
    mapping = ColumnMapping(
        target=None,
        prediction=None,
        numerical_features=numeric_features,
        categorical_features=categorical_features,
    )
    print(f"Reference: {reference.shape}. Current: {current.shape}.", flush=True)

    report = Report(metrics=[DataQualityPreset(), DataDriftPreset()])
    report.run(reference_data=reference, current_data=current, column_mapping=mapping)

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    report.save_html(str(reports / "drift_report.html"))
    report.save_json(str(reports / "drift_report.json"))

    reference_rows = json.dumps(reference.index.to_list(), separators=(",", ":"))
    provenance = {
        "evidently_version": evidently.__version__,
        "reference_model": model,
        "split": {**split, "stratify": "Churn"},
        "reference": {
            "source": HISTORICAL.as_posix(),
            "source_sha256": sha256(ROOT / HISTORICAL),
            "ordered_training_indices_sha256": hashlib.sha256(reference_rows.encode()).hexdigest(),
            "rows": len(reference),
            "columns": reference.shape[1],
        },
        "current": {
            "source": CURRENT.as_posix(),
            "source_sha256": sha256(ROOT / CURRENT),
            "rows": len(current),
            "columns": current.shape[1],
        },
        "features": {"numerical": numeric_features, "categorical": categorical_features},
    }
    (reports / "drift_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print("Saved reports/drift_report.html, drift_report.json and drift_provenance.json.", flush=True)


if __name__ == "__main__":
    main()
