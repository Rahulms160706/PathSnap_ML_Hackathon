# PathSnap – Laptop 2 (Frontend & Evaluator Dashboard)

Geospatial Intelligence, Map-Matching & Route Analytics Dashboard for PathSnap (PES University CSE ML Hackathon).

## System Architecture

PathSnap operates across a two-laptop distributed architecture:
- **Laptop 1 (Teammate)**: Hosts ML classifiers, Bayesian hyperparameter optimization, HMM transition/emission models, Viterbi route decoding, and the FastAPI server.
- **Laptop 2 (Rahul)**: Hosts the React + Vite evaluator dashboard, interactive Leaflet geospatial engine, trip selector, multi-layer route visualization, and real-time evaluation metrics displays.

---

## Features & Implementation

### 1. Interactive Leaflet Geospatial Engine
- **Dark Matter Basemap**: CartoDB Dark Matter / OpenStreetMap tiles matching the dark charcoal theme.
- **Multi-Layer Geospatial Rendering**:
  - **Raw GPS Observations**: Cyan circle markers (`#06b6d4`) with inspection popups (coordinates, timestamp, speed).
  - **GPS Trajectory Line**: Cyan dashed line connecting consecutive observations.
  - **Road Network Geometry**: Slate gray lines (`#64748b`) representing candidate road segments.
  - **Predicted HMM/Viterbi Route**: Prominent emerald polyline (`#10b981`) with route start/end origin markers.
  - **Reference Route (Ground Truth)**: Dashed violet polyline (`#a855f7`), rendered **strictly** when authorized and returned by the server-side evaluation interface.
- **Dynamic Auto-Fit (`FitBounds`)**: Automatically calculates the bounding box across all active coordinates and animates the viewport smoothly.

### 2. Independent Layer Controls & Legend
- **Floating Layer Controls**: Collapsible card in the top-right corner with independent checkboxes for all 5 layers, including live point/arc counters.
- **Floating Legend**: Positioned at bottom-left with color-coded keys and line patterns.

### 3. Evaluator Workflow & Trip Selection
- **Dynamic Trip Retrieval**: Fetches available evaluation trips from Laptop 1 (`GET /api/trips`).
- **Reconstruction Trigger**: Sends trip ID to `POST /api/predict`, with loading spinners and error handling.
- **Offline Development Fixture**: Allows offline map testing and demonstration even before Laptop 1 is running, with zero fabricated metrics.

### 4. Quantitative Evaluation Metrics
Displays metrics computed server-side:
- Route Accuracy
- Precision & Recall
- Macro F1
- Log Loss
- Route Continuity
- Total Inference Latency (ms)
- Active Pipeline Parameters (Classifier, Decoder, Transition Beta, Emission Sigma, Candidate Search Radius)

---

## How to Run

### Development Mode
```bash
cd frontend
npm install
npm run dev
```
Accessible at:
- Local: `http://localhost:5173/`
- Network: `http://10.30.202.22:5173/`

### Production Build
```bash
cd frontend
npm run build
npm run preview
```

### Two-Laptop Setup
1. Laptop 1 runs FastAPI:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
2. Open the dashboard in Laptop 2's browser.
3. Click **"Configure IP"** in the top header and enter Laptop 1's IP (e.g. `http://10.30.xxx.xxx:8000`).
4. Click **"Test Ping"** and **"Save & Apply"**.
