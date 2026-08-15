"""Print the saved Random Forest evaluation metrics in the terminal."""

import json
from pathlib import Path


METRICS_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "random_forest_metrics.json"


def main() -> None:
    report = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    print(f"Training rows: {report['train_rows']}")
    print(f"Testing rows: {report['test_rows']}")
    for name, value in report["metrics"].items():
        print(f"{name.replace('_', ' ').title()}: {value:.2%}")


if __name__ == "__main__":
    main()
