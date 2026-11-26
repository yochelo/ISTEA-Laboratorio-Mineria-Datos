import json
from unittest.mock import Mock

import pytest

import app.main as api


CATEGORICAL_FIELDS = (
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
)

INTERNET_FIELDS = (
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
)
NO_INTERNET = {
    "InternetService": "No", **dict.fromkeys(INTERNET_FIELDS, "No internet service"),
}


@pytest.mark.dvc
@pytest.mark.parametrize("changes", [
    {},
    {"SeniorCitizen": 1, "tenure": 72, "MonthlyCharges": 130, "TotalCharges": 0},
    {"tenure": 0, "MonthlyCharges": 1, "TotalCharges": None},
    {"PhoneService": "No", "MultipleLines": "No phone service", **NO_INTERNET},
])
def test_valid_requests_predict(client, sample_customer, changes):
    response = client.post("/predict", json=sample_customer | changes)
    assert response.status_code == 200
    assert 0 <= response.json()["probability"] <= 1


@pytest.mark.dvc
def test_total_charges_can_be_omitted(client, sample_customer):
    payload = {field: value for field, value in sample_customer.items() if field != "TotalCharges"}
    explicit_null = client.post("/predict", json=payload | {"TotalCharges": None})
    omitted = client.post("/predict", json=payload)
    assert explicit_null.status_code == omitted.status_code == 200
    explicit_result, omitted_result = explicit_null.json(), omitted.json()
    assert explicit_result.pop("request_id") == explicit_null.headers["X-Request-ID"]
    assert omitted_result.pop("request_id") == omitted.headers["X-Request-ID"]
    assert explicit_null.headers["X-Request-ID"] != omitted.headers["X-Request-ID"]
    assert explicit_result == omitted_result


@pytest.mark.parametrize(("changes", "expected"), [
    ({"tenure": -12, "Contract": "Weekly", "MonthlyCharges": "not-a-number"},
     {"tenure", "Contract", "MonthlyCharges"}),
    *[({field: "Unknown"}, {field}) for field in CATEGORICAL_FIELDS],
    ({"SeniorCitizen": -1}, {"SeniorCitizen"}),
    ({"SeniorCitizen": 2}, {"SeniorCitizen"}),
    ({"SeniorCitizen": True}, {"SeniorCitizen"}),
    ({"SeniorCitizen": "0"}, {"SeniorCitizen"}),
    ({"tenure": 73}, {"tenure"}),
    ({"tenure": 32.0}, {"tenure"}),
    ({"tenure": False}, {"tenure"}),
    ({"MonthlyCharges": 0}, {"MonthlyCharges"}),
    ({"MonthlyCharges": -1}, {"MonthlyCharges"}),
    ({"MonthlyCharges": "101.35"}, {"MonthlyCharges"}),
    ({"MonthlyCharges": True}, {"MonthlyCharges"}),
    ({"TotalCharges": -1}, {"TotalCharges"}),
    ({"TotalCharges": "2865.88"}, {"TotalCharges"}),
    ({"TotalCharges": False}, {"TotalCharges"}),
    ({"customerID": "extra"}, {"customerID"}),
    *[({field: value}, {field}) for field in ("MonthlyCharges", "TotalCharges")
      for value in (float("nan"), float("inf"), float("-inf"))],
])
def test_invalid_fields_stop_before_inference(contract_client, sample_customer, monkeypatch, changes, expected):
    inference = Mock()
    monkeypatch.setattr(api, "predict_churn", inference)
    response = contract_client.post(
        "/predict", content=json.dumps(sample_customer | changes),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert {item["loc"][-1] for item in response.json()["detail"]} == expected
    inference.assert_not_called()


@pytest.mark.parametrize(("changes", "field"), [
    ({"PhoneService": "No"}, "MultipleLines"),
    ({"MultipleLines": "No phone service"}, "MultipleLines"),
    *[({field: "No internet service"}, field) for field in INTERNET_FIELDS],
    *[(NO_INTERNET | {field: "No"}, field) for field in INTERNET_FIELDS],
])
def test_inconsistent_services_stop_before_inference(contract_client, sample_customer, monkeypatch, changes, field):
    inference = Mock()
    monkeypatch.setattr(api, "predict_churn", inference)
    response = contract_client.post("/predict", json=sample_customer | changes)
    assert response.status_code == 422
    error, = response.json()["detail"]
    assert error["loc"] == ["body"]
    assert field in error["msg"]
    inference.assert_not_called()


def test_openapi_describes_customer_input(contract_client, sample_customer):
    spec = contract_client.get("/openapi.json").json()
    schema = spec["components"]["schemas"]["CustomerInput"]
    properties = schema["properties"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(sample_customer) - {"TotalCharges"}
    for name, value in sample_customer.items():
        if isinstance(value, str):
            assert properties[name]["type"] == "string"
            assert value in properties[name]["enum"]
    assert set(properties["PaymentMethod"]["enum"]) == {
        "Electronic check", "Mailed check", "Bank transfer (automatic)",
        "Credit card (automatic)",
    }
    for name, maximum in (("SeniorCitizen", 1), ("tenure", 72)):
        assert properties[name]["type"] == "integer"
        assert (properties[name]["minimum"], properties[name]["maximum"]) == (0, maximum)
    assert properties["MonthlyCharges"]["exclusiveMinimum"] == 0
    assert properties["TotalCharges"]["anyOf"] == [
        {"type": "number", "minimum": 0.0}, {"type": "null"},
    ]
    assert "PhoneService" in schema["description"] and "InternetService" in schema["description"]
    assert "422" in spec["paths"]["/predict"]["post"]["responses"]
