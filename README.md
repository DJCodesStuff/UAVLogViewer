# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

A modern UAV log viewer with AI-powered analysis. The frontend (Vue) visualizes MAVLink/Dataflash logs; the backend (Flask + Gemini) ingests telemetry, builds retrieval context, and answers questions grounded in your data.

## Project Overview

- Frontend: Interactive plots and 3D flight visualization with a built-in chat panel.
- Backend: Session-based RAG (retrieval augmented generation), Gemini integration, optional Qdrant vector search, and per-session artifacts in `rag_docs/`.

## Quick Start

1) Frontend
```bash
git clone <repository-url>
cd UAVLogViewer
npm install
export VUE_APP_CESIUM_TOKEN=<your-cesium-token>
npm run dev
```
or
```bash
docker build -t uav-log-viewer-frontend .
docker run -p 8080:8080 -e VUE_APP_CESIUM_TOKEN="<cesium_token>" uav-log-viewer-frontend
```

2) Backend (deployment & configuration)

Please follow the backend deployment guide here:
- backend_api/README.md

That guide covers environment variables, Qdrant setup, running the API, and the full request cycle (upload → ingestion → indexing → chat).

## Access

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000 (see health at `/api/health`)

## Docker

```bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

## Documentation

- Backend deployment and details: backend_api/README.md

## License

This project is part of the ArduPilot ecosystem. See the main repository for license details.
