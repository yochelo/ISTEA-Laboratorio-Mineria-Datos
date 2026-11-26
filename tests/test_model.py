import pytest

from app.model_loader import load_model
from app.schemas import CustomerInput


@pytest.mark.dvc
def test_load_approved_model():
    model, identity = load_model()
    assert identity == "ISTEA_Churn/1"
    assert set(model.classes_) == {"No", "Yes"}
    assert set(model.feature_names_in_) == set(CustomerInput.model_fields)
