
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

def split_data(df):
    X = df.drop(columns=["customerID", "Churn"])
    y = df["Churn"]

    return train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
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
    df = load_data("data/raw/customer_churn_historical.csv")

    X_train, X_test, y_train, y_test = split_data(df)

    classifiers = {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest": RandomForestClassifier(random_state=42)
    }

    selected_model = None

    for name, classifier in classifiers.items():
        model = train_model(X_train, y_train, classifier)
        metrics = evaluate_model(model, X_test, y_test)

        if name == "Logistic Regression":
            selected_model = model

        print(f"\n{name}")
        print(f"Accuracy: {metrics['accuracy']:.3f}")
        print(f"Precision: {metrics['precision']:.3f}")
        print(f"Recall: {metrics['recall']:.3f}")
        print(f"F1-score: {metrics['f1']:.3f}")

    joblib.dump(selected_model, "models/churn_model.joblib")
    print("\nModelo guardado en models/churn_model.joblib")

if __name__ == "__main__":
    main()