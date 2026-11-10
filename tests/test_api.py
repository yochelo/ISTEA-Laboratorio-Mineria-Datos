
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
        assert result["prediction"] in ["Yes", "No"]
        assert 0 <= result["probability"] <= 1


    def test_predict_invalid():
        response = client.post("/predict", json={})

        assert response.status_code == 422
