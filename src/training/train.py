
# Entrenamiento de los modelos del proyecto.

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

from src.data.load_data import load_data
from src.features.build_preprocessor import build_preprocessor

from src.evaluation.evaluate import evaluate_model
import joblib
import json
import yaml

def split_data(df, test_size, random_state):
    X = df.drop(columns=["customerID", "Churn"])
    y = df["Churn"]

    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

def train_model(X_train, y_train, classifier):
    preprocessor = build_preprocessor()

    model = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", classifier)
    ])

    model.fit(X_train, y_train)

    return model

def main():
    with open("params.yaml", "r") as file:
        params = yaml.safe_load(file)

    df = load_data("data/raw/customer_churn_historical.csv")

    X_train, X_test, y_train, y_test = split_data(
        df,
        params["split"]["test_size"],
        params["split"]["random_state"]
    )

    classifiers = {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(
            max_iter=params["model"]["logistic_regression"]["max_iter"]
        ),
        "Random Forest": RandomForestClassifier(random_state=42)
    }

    selected_model = None
    selected_metrics = None

    for name, classifier in classifiers.items():
        model = train_model(X_train, y_train, classifier)
        metrics = evaluate_model(model, X_test, y_test)

        if name == "Logistic Regression":
            selected_model = model
            selected_metrics = metrics

        print(f"\n{name}")
        print(f"Accuracy: {metrics['accuracy']:.3f}")
        print(f"Precision: {metrics['precision']:.3f}")
        print(f"Recall: {metrics['recall']:.3f}")
        print(f"F1-score: {metrics['f1']:.3f}")

    joblib.dump(selected_model, "models/churn_model.joblib")

    with open("reports/metrics.json", "w") as file:
        json.dump(selected_metrics, file, indent=4)

    print("\nModelo guardado en models/churn_model.joblib")
    print("Métricas guardadas en reports/metrics.json")

if __name__ == "__main__":
    main()