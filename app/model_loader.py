import hashlib
import json
from io import BytesIO
from pathlib import Path

import joblib

from app.schemas import CustomerInput

MANIFEST_PATH = Path(__file__).with_name("model_manifest.json")
MODEL_PATH = MANIFEST_PATH.parent.parent / "models" / "churn_model.joblib"


def load_model():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = ("registry_name", "version", "run_id", "training_commit", "sha256")
    if not all(isinstance(manifest[key], str) and manifest[key] for key in required):
        raise ValueError("Invalid model manifest")

    content = MODEL_PATH.read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
        raise ValueError("Model artifact SHA-256 does not match the manifest")

    model = joblib.load(BytesIO(content))
    if (
        not callable(getattr(model, "predict", None))
        or not callable(getattr(model, "predict_proba", None))
        or sorted(getattr(model, "classes_", ())) != ["No", "Yes"]
        or set(getattr(model, "feature_names_in_", ())) != set(CustomerInput.model_fields)
    ):
        raise ValueError("Model is incompatible with the inference contract")
    return model, f"{manifest['registry_name']}/{manifest['version']}"
