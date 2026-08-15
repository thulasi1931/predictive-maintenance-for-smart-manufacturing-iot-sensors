"""Make one machine-failure prediction from sensor values.

Example:
python ml/predict_failure.py --type M --air-temp 300.1 --process-temp 310.6 --speed 1500 --torque 40 --tool-wear 100
"""

import argparse
from pathlib import Path

import joblib
import pandas as pd

from feature_engineering import add_engineered_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict machine failure from one sensor reading.")
    parser.add_argument("--type", choices=["L", "M", "H"], required=True, help="Product quality type")
    parser.add_argument("--air-temp", type=float, required=True, help="Air temperature in Kelvin")
    parser.add_argument("--process-temp", type=float, required=True, help="Process temperature in Kelvin")
    parser.add_argument("--speed", type=float, required=True, help="Rotational speed in rpm")
    parser.add_argument("--torque", type=float, required=True, help="Torque in Nm")
    parser.add_argument("--tool-wear", type=float, required=True, help="Tool wear in minutes")
    parser.add_argument("--model", type=Path, default=Path("artifacts/random_forest_failure_model.joblib"))
    args = parser.parse_args()

    raw_reading = pd.DataFrame([{
        "Type": args.type,
        "Air temperature [K]": args.air_temp,
        "Process temperature [K]": args.process_temp,
        "Rotational speed [rpm]": args.speed,
        "Torque [Nm]": args.torque,
        "Tool wear [min]": args.tool_wear,
    }])

    model = joblib.load(args.model)
    features = add_engineered_features(raw_reading)
    failure_probability = model.predict_proba(features)[0, 1]
    prediction = int(failure_probability >= 0.5)

    print("Machine failure prediction:", "FAILURE RISK" if prediction else "NORMAL")
    print(f"Failure probability: {failure_probability:.2%}")
    print("Recommended action:", "Inspect machine now." if prediction else "Continue monitoring.")


if __name__ == "__main__":
    main()
