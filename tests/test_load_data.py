import pytest
from pandas.api.types import is_float_dtype, is_integer_dtype, is_string_dtype

from app.schemas import CustomerInput
from src.data.load_data import load_data


@pytest.mark.dvc
def test_load_data():
    df = load_data("data/raw/customer_churn_historical.csv")

    assert len(df) == 7043
    assert set(df.columns) == {"customerID", "Churn", *CustomerInput.model_fields}
    assert df["customerID"].is_unique and is_string_dtype(df["customerID"])
    assert set(df["Churn"]) == {"Yes", "No"}
    assert all(is_integer_dtype(df[name]) for name in ("SeniorCitizen", "tenure"))
    assert all(is_float_dtype(df[name]) for name in ("MonthlyCharges", "TotalCharges"))
