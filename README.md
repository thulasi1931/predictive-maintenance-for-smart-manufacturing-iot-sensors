# MaintAI: Predictive Maintenance for Smart Manufacturing

A student hackathon project that simulates IoT sensor telemetry and uses Random Forest machine learning to predict machine-failure risk and likely failure causes.

## Features

- Binary failure-risk prediction using the AI4I 2020 dataset.
- Failure-type predictions: Tool Wear, Heat Dissipation, Power, Overstrain, and Random Failure.
- React dashboard for manual input and live browser simulation.
- Flask REST API and SQLite prediction/alert history.
- Warning and critical maintenance alerts; users can mark alerts resolved.

## Folder guide

- `ml/` — feature engineering and model training scripts.
- `artifacts/` — trained Random Forest model files and evaluation results.
- `backend/` — Flask prediction API.
- `frontend/` — React/Vite dashboard.
- `database/` — SQLite helper and local `maintenance.db` data file.
- `simulator/` — terminal-based IoT sensor simulator.

## Run locally

Open three PowerShell terminals in the project root.

1. Start the API:

```powershell
python backend/app.py
```

2. Start the dashboard:

```powershell
cd frontend
npm run dev
```

Open the localhost URL printed by Vite, normally `http://localhost:5173`.

3. Optional terminal simulator:

```powershell
python simulator/sensor_simulator.py
```

## Advanced dashboard features

- Search a machine ID such as `M-101` to load only that machine's stored telemetry.
- The sensor comparison chart overlays air/process temperature, rotational speed, torque, and tool wear from the selected machine's history.
- Each prediction shows a maintenance priority, simple sensor-based risk reasons, and estimated downtime cost at risk, using the business value of $15,000 per downtime hour.

## Model evaluation

The binary Random Forest was evaluated with a stratified split: 8,000 training rows and 2,000 unseen testing rows. It achieved 99.05% accuracy, 77.94% failure recall, and 86.13% PR-AUC. See `artifacts/random_forest_metrics.json`.

Accuracy alone is not enough because failures are only 3.39% of the AI4I data; recall, F1, and PR-AUC are also reported.
