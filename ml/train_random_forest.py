"""Train a Random Forest model for AI4I machine-failure prediction."""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from feature_engineering import add_engineered_features


DATA_PATH = Path(r"C:\Users\Yadda\Downloads\ai4i+2020+predictive+maintenance+dataset\ai4i2020.csv")
OUTPUT_DIRECTORY = Path("artifacts")
RANDOM_STATE = 42


def build_random_forest_model() -> Pipeline:
    """Create preprocessing plus a class-balanced Random Forest classifier."""
    numeric_columns = [
        "Air temperature [K]", "Process temperature [K]",
        "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
        "Temperature difference [K]", "Power [W]",
    ]
    preprocessor = ColumnTransformer([
        ("product_type", OneHotEncoder(handle_unknown="ignore"), ["Type"]),
        ("sensor_values", "passthrough", numeric_columns),
    ])
    classifier = RandomForestClassifier(
        n_estimators=500,
        class_weight="balanced",
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessor), ("model", classifier)])


def main() -> None:
    data = pd.read_csv(DATA_PATH)
    features = add_engineered_features(data)
    target = data["Machine failure"]
    X_train, X_test, y_train, y_test = train_test_split(
        features, target, test_size=0.20, stratify=target, random_state=RANDOM_STATE
    )

    # Evaluate on data that the model has not seen during training.
    evaluation_model = build_random_forest_model()
    evaluation_model.fit(X_train, y_train)
    probabilities = evaluation_model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.50).astype(int)
    metrics = {
        "accuracy": round(accuracy_score(y_test, predictions), 4),
        "balanced_accuracy": round(balanced_accuracy_score(y_test, predictions), 4),
        "precision": round(precision_score(y_test, predictions, zero_division=0), 4),
        "recall": round(recall_score(y_test, predictions, zero_division=0), 4),
        "f1_score": round(f1_score(y_test, predictions, zero_division=0), 4),
        "pr_auc": round(average_precision_score(y_test, probabilities), 4),
        "roc_auc": round(roc_auc_score(y_test, probabilities), 4),
    }

    OUTPUT_DIRECTORY.mkdir(exist_ok=True)
    with (OUTPUT_DIRECTORY / "random_forest_metrics.json").open("w", encoding="utf-8") as file:
        json.dump({"train_rows": len(X_train), "test_rows": len(X_test), "metrics": metrics}, file, indent=2)

    # Refit with every labelled row for the saved application model.
    final_model = build_random_forest_model()
    final_model.fit(features, target)
    joblib.dump(final_model, OUTPUT_DIRECTORY / "random_forest_failure_model.joblib")

    print("Random Forest evaluation (8,000 train rows / 2,000 test rows):")
    print(json.dumps(metrics, indent=2))
    print("Saved model: artifacts/random_forest_failure_model.joblib")


if __name__ == "__main__":
    main()
