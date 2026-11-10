
from fastapi.testclient import TestClient

from app.main import app


# TestClient permite probar la API sin levantar Uvicorn.
with TestClient(app) as client:

    def test_health():
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


    def test_predict():
        customer = {
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
            "TotalCharges": 151.0
        }

        response = client.post("/predict", json=customer)

        assert response.status_code == 200
        
        result = response.json()

        assert set(result.keys()) == {
            "prediction",
            "probability",
            "risk_level",
            "model_version"
        }

        assert result["prediction"] in ["Yes", "No"]
        assert isinstance(result["probability"], float)
        assert 0 <= result["probability"] <= 1

        assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert result["model_version"] == "1"

        probability = result["probability"]

        if probability < 0.30:
            assert result["risk_level"] == "LOW"
        elif probability < 0.70:
            assert result["risk_level"] == "MEDIUM"
        else:
            assert result["risk_level"] == "HIGH"

    def test_predict_invalid():
        response = client.post("/predict", json={})

        assert response.status_code == 422
