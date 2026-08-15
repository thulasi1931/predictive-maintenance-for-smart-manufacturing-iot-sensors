"""Software-only IoT sensor simulator for the predictive-maintenance demo.

Run this while the Flask backend is running:
    python simulator/sensor_simulator.py
"""

import json
import random
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


API_URL = "http://127.0.0.1:5000/predict"
INTERVAL_SECONDS = 5


def create_sensor_reading() -> dict:
    """Create one realistic AI4I-style software sensor telemetry record."""
    air_temperature = round(random.uniform(298.0, 302.0), 1)
    return {
        "machine_id": f"M-{random.randint(101, 105)}",
        "type": random.choices(["L", "M", "H"], weights=[60, 30, 10])[0],
        "air_temperature": air_temperature,
        "process_temperature": round(air_temperature + random.uniform(8.0, 12.0), 1),
        "rotational_speed": random.randint(1200, 1900),
        "torque": round(random.uniform(25.0, 60.0), 1),
        "tool_wear": random.randint(0, 250),
    }


def request_prediction(reading: dict) -> dict:
    """Send simulated telemetry to Flask and return its ML prediction."""
    request = Request(
        API_URL,
        data=json.dumps(reading).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    print("IoT sensor simulator started. Press Ctrl+C to stop.")
    while True:
        sensor_reading = create_sensor_reading()
        try:
            prediction = request_prediction(sensor_reading)
            print(
                f"Telemetry: {sensor_reading} | "
                f"Result: {prediction['prediction']} "
                f"({prediction['failure_probability_percent']}%)"
            )
        except URLError:
            print("Cannot reach the backend. Start it with: python backend/app.py")
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
