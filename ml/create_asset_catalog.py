"""Create a reusable Product ID catalog from the original AI4I dataset."""

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/asset_catalog.json"))
    args = parser.parse_args()

    data = pd.read_csv(args.data)
    assets = [
        {
            "asset_id": row["Product ID"],
            "product_type": row["Type"],
            "air_temperature": row["Air temperature [K]"],
            "process_temperature": row["Process temperature [K]"],
            "rotational_speed": row["Rotational speed [rpm]"],
            "torque": row["Torque [Nm]"],
            "tool_wear": row["Tool wear [min]"],
        }
        for _, row in data.drop_duplicates("Product ID").iterrows()
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(assets), encoding="utf-8")
    print(f"Saved {len(assets)} AI4I Product IDs to {args.output}")


if __name__ == "__main__":
    main()
