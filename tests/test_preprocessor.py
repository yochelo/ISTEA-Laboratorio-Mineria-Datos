import pandas as pd
import pytest

from src.features.build_preprocessor import build_preprocessor


def test_preprocessor(sample_customer):
    features = pd.DataFrame([
        sample_customer | {"TotalCharges": 100.0},
        sample_customer | {"TotalCharges": 300.0},
        sample_customer | {"TotalCharges": None},
    ])
    preprocessor = build_preprocessor()
    transformed = preprocessor.fit_transform(features)

    names = list(preprocessor.get_feature_names_out())
    assert transformed.shape == (len(features), len(names))
    assert "cat__gender_Male" in names
    charges = names.index("num__TotalCharges")
    assert transformed[0, charges] < transformed[2, charges] < transformed[1, charges]
    assert transformed[2, charges] == pytest.approx(0.0)
