"""Train separate Random Forest models for each AI4I failure cause.

Separate binary models correctly support records with more than one cause.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from feature_engineering import add_engineered_features
from train_random_forest import build_random_forest_model


DATA_PATH = Path(r"C:\Users\Yadda\Downloads\ai4i+2020+predictive+maintenance+dataset\ai4i2020.csv")
OUTPUT_DIRECTORY = Path("artifacts")
FAILURE_TYPES = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
    "RNF": "Random Failure",
}


def main() -> None:
    data = pd.read_csv(DATA_PATH)
    features = add_engineered_features(data)
    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    metrics = {}
    trained_models = {}

    for code, label in FAILURE_TYPES.items():
        X_train, X_test, y_train, y_test = train_test_split(
            features, data[code], test_size=0.20, stratify=data[code], random_state=42
        )
        evaluation_model = build_random_forest_model()
        evaluation_model.fit(X_train, y_train)
        probabilities = evaluation_model.predict_proba(X_test)[:, 1]
        predictions = (probabilities >= 0.50).astype(int)
        metrics[code] = {
            "label": label,
            "positive_cases": int(data[code].sum()),
            "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
            "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
            "pr_auc": round(average_precision_score(y_test, probabilities), 4),
        }

        # After evaluation, fit the version used by the Flask application on all data.
        final_model = build_random_forest_model()
        final_model.fit(features, data[code])
        trained_models[code] = final_model
        print(f"Trained {label}: {int(data[code].sum())} positive examples")

    joblib.dump(trained_models, OUTPUT_DIRECTORY / "failure_type_models.joblib")
    with (OUTPUT_DIRECTORY / "failure_type_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)
    print("Saved: artifacts/failure_type_models.joblib")


if __name__ == "__main__":
    main()
