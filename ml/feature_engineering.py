"""Reusable feature preparation for the AI4I predictive-maintenance dataset."""

import pandas as pd


RAW_FEATURES = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]


def add_engineered_features(sensor_data: pd.DataFrame) -> pd.DataFrame:
    """Return model features without identifiers or failure labels.

    The calculations use readings from the current observation only, so they
    can be calculated safely for live IoT telemetry without data leakage.
    """
    missing_columns = set(RAW_FEATURES) - set(sensor_data.columns)
    if missing_columns:
        raise ValueError(f"Missing required sensor columns: {sorted(missing_columns)}")

    features = sensor_data[RAW_FEATURES].copy()
    features["Temperature difference [K]"] = (
        features["Process temperature [K]"] - features["Air temperature [K]"]
    )
    # Mechanical power estimate: P = torque * angular velocity.
    features["Power [W]"] = (
        2 * 3.141592653589793 * features["Rotational speed [rpm]"] * features["Torque [Nm]"] / 60
    )
    return features
