from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.main as api


@pytest.fixture
def sample_customer():
    # Official valid example. Each test can change its own copy.
    return {
        "gender": "Male",
        "SeniorCitizen": 0,
        "Partner": "No",
        "Dependents": "No",
        "tenure": 32,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "Yes",
        "Contract": "Month-to-month",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Mailed check",
        "MonthlyCharges": 101.35,
        "TotalCharges": 2865.88,
    }


@pytest.fixture
def client():
    with TestClient(api.app) as test_client:
        yield test_client
    assert api.app.state.model is None
    assert api.app.state.model_version is None


@pytest.fixture
def contract_client(monkeypatch):
    model = SimpleNamespace(
        classes_=["No", "Yes"],
        predict=lambda _: ["Yes"],
        predict_proba=lambda _: [[0.2, 0.8]],
    )
    monkeypatch.setattr(api, "load_model", lambda: (model, "test/1"))
    with TestClient(api.app) as test_client:
        yield test_client
