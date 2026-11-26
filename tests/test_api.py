import hashlib
import json
from types import SimpleNamespace
from uuid import UUID

import joblib
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.model_loader as loader
from app.inference import predict_churn, risk_level
from app.main import app
from app.schemas import CustomerInput


CUSTOMER = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 2,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 75.5,
    "TotalCharges": 151.0,
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_version": "ISTEA_Churn/1"}
    assert client.get("/live").json() == {"status": "alive"}
    readiness = client.get("/ready")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready"}


def test_predict(client):
    response = client.post("/predict", json=CUSTOMER)
    assert response.status_code == 200
    result = response.json()
    assert set(result) == {"prediction", "probability", "risk_level", "model_version", "request_id"}
    assert result["model_version"] == "ISTEA_Churn/1"
    assert result["request_id"] == response.headers["X-Request-ID"]
    assert UUID(result["request_id"]).version == 4
    assert client.post("/predict", json=CUSTOMER).headers["X-Request-ID"] != result["request_id"]

    pipeline = joblib.load(loader.MODEL_PATH)
    features = pd.DataFrame([CUSTOMER])
    index = list(pipeline.classes_).index("Yes")
    assert result["prediction"] == pipeline.predict(features)[0]
    assert result["probability"] == pipeline.predict_proba(features)[0][index]
    assert 0 <= result["probability"] <= 1
    assert result["risk_level"] == risk_level(result["probability"])


def test_predict_invalid(client):
    response = client.post("/predict", json={})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert UUID(response.headers["X-Request-ID"]).version == 4


def test_load_approved_model():
    model, identity = loader.load_model()
    assert identity == "ISTEA_Churn/1"
    assert set(model.classes_) == {"No", "Yes"}


def test_digest_mismatch_stops_before_deserialization(tmp_path, monkeypatch):
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"unexpected content")
    monkeypatch.setattr(loader, "MODEL_PATH", artifact)

    def fail_if_called(*args):
        pytest.fail("Invalid artifact was passed to joblib.load")

    monkeypatch.setattr(loader.joblib, "load", fail_if_called)
    with pytest.raises(ValueError, match="SHA-256"):
        loader.load_model()


def test_loader_rejects_unexpected_classes(monkeypatch):
    model = SimpleNamespace(
        predict=lambda features: ["No"],
        predict_proba=lambda features: [[1.0]],
        classes_=["No"],
        feature_names_in_=list(CustomerInput.model_fields),
    )
    monkeypatch.setattr(loader.joblib, "load", lambda _: model)
    with pytest.raises(ValueError, match="incompatible"):
        loader.load_model()


@pytest.mark.parametrize("state", ["missing", "wrong_hash", "corrupt", "incompatible"])
def test_unavailable_model_preserves_liveness(state, tmp_path, monkeypatch):
    artifact = tmp_path / "model.joblib"
    monkeypatch.setattr(loader, "MODEL_PATH", artifact)
    if state in ("wrong_hash", "corrupt"):
        artifact.write_bytes(b"not a valid joblib file")
    if state == "incompatible":
        joblib.dump({"classes_": ["No", "Yes"]}, artifact)
    if state in ("corrupt", "incompatible"):
        manifest = json.loads(loader.MANIFEST_PATH.read_text())
        manifest["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(manifest))
        monkeypatch.setattr(loader, "MANIFEST_PATH", path)

    with TestClient(app) as test_client:
        live = test_client.get("/live")
        assert live.status_code == 200
        assert live.json() == {"status": "alive"}
        for endpoint, status in (("/health", "unavailable"), ("/ready", "not_ready")):
            response = test_client.get(endpoint)
            assert response.status_code == 503
            assert response.json() == {"status": status}
        response = test_client.post("/predict", json=CUSTOMER)
        assert response.status_code == 503
        assert response.json() == {"detail": "Model unavailable"}
        assert UUID(response.headers["X-Request-ID"]).version == 4


def test_inference_exception_returns_generic_500(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(app.state.model, "predict", fail)
    response = client.post("/predict", json=CUSTOMER)
    assert response.status_code == 500
    assert response.json() == {"detail": "Inference failed"}
    assert UUID(response.headers["X-Request-ID"]).version == 4


@pytest.mark.parametrize("probabilities", [
    [0.8, float("nan")], [float("inf"), 0.2], [0.2, -0.1],
    [0.2, 1.1], [0.3, 0.3], [1.0],
])
def test_invalid_model_probabilities_return_500(client, monkeypatch, probabilities):
    monkeypatch.setattr(app.state.model, "predict_proba", lambda _: [probabilities])
    response = client.post("/predict", json=CUSTOMER)
    assert response.status_code == 500
    assert response.json() == {"detail": "Inference failed"}


def test_yes_probability_can_be_first():
    class ReversedClasses:
        classes_ = ["Yes", "No"]

        def predict(self, features):
            return ["Yes"]

        def predict_proba(self, features):
            return [[0.75, 0.25]]

    assert predict_churn(ReversedClasses(), CustomerInput(**CUSTOMER)) == {
        "prediction": "Yes", "probability": 0.75, "risk_level": "HIGH",
    }


@pytest.mark.parametrize(("probability", "expected"), [
    (0.0, "LOW"), (0.299999, "LOW"), (0.30, "MEDIUM"),
    (0.699999, "MEDIUM"), (0.70, "HIGH"), (1.0, "HIGH"),
])
def test_risk_boundaries(probability, expected):
    assert risk_level(probability) == expected
