# AquaVigil Backend

**A Computer Vision Framework for Automated Fish Disease Detection in Aquaculture Systems**

AquaVigil provides an automated, reliable backend REST API service designed for early detection, localization, and classification of aquatic fish diseases. Built specifically for collaborative collegiate engineering projects, this backend interfaces smoothly with a Flutter mobile application, a Next.js web dashboard, and an AI/ML computer vision pipeline.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Directory Structure](#directory-structure)
- [Quick Start Guide](#quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Setup on macOS / Linux](#setup-on-macos--linux)
  - [Setup on Windows (PowerShell)](#setup-on-windows-powershell)
- [Running the Server](#running-the-server)
- [Running Automated Tests](#running-automated-tests)
- [Interactive API Documentation (Swagger & ReDoc)](#interactive-api-documentation-swagger--redoc)
- [API Overview & Sample Requests](#api-overview--sample-requests)
- [Environment Configuration](#environment-configuration)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
- [Teammate Handover Documentation](#teammate-handover-documentation)

---

## Key Features

1. **Robust Multipart Image Ingestion**:
   - Accepts JPEG and PNG formats.
   - Enforces a 10 MB upload ceiling with stream-based size checks to prevent RAM exhaustion.
   - Genuine file inspection using Pillow (verifies binary magic bytes, rejecting renamed `.txt` or `.exe` files).
   - Automatically standardizes RGBA and grayscale fish images into 3-channel RGB.
2. **Honest AI Integration Contract**:
   - Zero fabricated diagnoses or fake confidences.
   - Returns explicit `status: "model_not_configured"` until real weights are supplied by the ML teammate.
   - Optional, clearly labeled `[SIMULATED]` mock mode for frontend UI testing (`ENABLE_MOCK_MODEL=true`).
3. **Audit Trail & Statistics**:
   - Persists every analysis request to SQLite (default) or PostgreSQL.
   - Real-time aggregate statistics for dashboard monitoring.
4. **Developer-First Design**:
   - Zero paid cloud services or API keys required.
   - Automated table initialization on startup.
   - Isolated pytest suite with temporary SQLite database and upload fixtures.

---

## Tech Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ / 3.11+ | Clean type hints, modern asyncio support |
| **Web Framework** | FastAPI (v0.110+) | High performance, automatic OpenAPI documentation |
| **ASGI Server** | Uvicorn | Lightweight, production-grade asynchronous server |
| **ORM / Database** | SQLAlchemy (v2.0+) | SQLite for zero-cost local dev, PostgreSQL ready |
| **Validation** | Pydantic (v2.6+) & Settings | Strict request/response parsing and type safety |
| **Image Processing** | Pillow (PIL) | Deep image verification, format conversion |
| **Testing** | Pytest & HTTPX TestClient | Automated, deterministic unit & integration tests |

---

## Directory Structure

```text
aquavigil-backend/
├── app/
│   ├── main.py                     # FastAPI application setup and lifespan
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Pydantic Settings and environment config
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py             # SQLAlchemy engine, session maker, get_db dependency
│   │   └── models.py               # Analysis ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── analysis.py             # Analysis, BoundingBox, and History schemas
│   │   ├── health.py               # Health check schemas
│   │   └── stats.py                # Dashboard statistics schemas
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py           # /health and /api/v1/health endpoints
│   │       ├── analysis.py         # /analyses upload, history, get, delete
│   │       └── statistics.py       # /analyses/stats endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── image_service.py        # Image validation, RGB conversion, storage
│   │   ├── prediction_service.py   # AI inference abstraction & PyTorch template
│   │   └── explanation_service.py  # Grad-CAM / XAI metadata handling
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Isolated SQLite and storage fixtures
│       ├── test_health.py          # Health check endpoint tests
│       ├── test_analysis.py        # Comprehensive image analysis tests
│       └── test_statistics.py      # Aggregate stats calculations tests
├── storage/
│   ├── .gitkeep                    # Storage directory placeholder
│   └── uploads/                    # Local storage folder for uploaded images
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules
├── requirements.txt                # Production and testing dependencies
├── README.md                       # This document
├── API_DOCUMENTATION.md            # Complete API endpoints and schemas reference
├── FRONTEND_INTEGRATION.md         # Guide for Flutter and Next.js developers
├── AI_MODEL_INTEGRATION.md         # Specification for AI/ML teammate
├── HANDOVER_CHECKLIST.md           # Pre-integration checklist
└── run.py                          # Terminal runner with server banner
```

---

## Quick Start Guide

### Prerequisites

- Python 3.10, 3.11, or compatible installed.
- Git (optional, for version tracking).

---

### Setup on macOS / Linux

1. **Clone or navigate into the repository**:
   ```bash
   cd AquaVigil
   ```

2. **Create a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Install required dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Create your local configuration**:
   ```bash
   cp .env.example .env
   ```

---

### Setup on Windows (PowerShell)

1. **Navigate into the folder**:
   ```powershell
   cd AquaVigil
   ```

2. **Create virtual environment**:
   ```powershell
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   ```powershell
   .venv\Scripts\Activate.ps1
   ```
   *(If execution policies block this script, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

4. **Install dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Create your local configuration**:
   ```powershell
   Copy-Item .env.example .env
   ```

---

## Running the Server

Start the development server with automatic code reloading:

```bash
# Using the bundled runner (recommended):
python run.py

# Or directly with Uvicorn:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once started, the server outputs the interactive banner:
```text
======================================================================
  Project     : AquaVigil Backend (v1.0.0)
  Environment : development
  Database    : ./storage/aquavigil.db
  Base URL    : http://0.0.0.0:8000
  Health Check: http://0.0.0.0:8000/health
  Swagger Docs: http://0.0.0.0:8000/docs
======================================================================
```

---

## Running Automated Tests

Run the complete test suite:

```bash
pytest -v
```

The test runner will execute all 21 automated test cases verifying:
- Service health and dependency states
- Valid JPEG and PNG uploads (including RGBA-to-RGB conversion)
- Corrupted file rejection
- Non-image MIME type rejection (PDF, text)
- Files exceeding 10 MB upload ceiling
- Empty (0-byte) file handling
- Database audit logging
- History pagination (`limit` and `offset`)
- Single record retrieval and 404 responses
- Aggregate statistics calculation
- Explainability (Grad-CAM) availability responses
- Inference failure graceful recovery (`status: "failed"`)
- Safe record and file deletion

---

## Interactive API Documentation (Swagger & ReDoc)

Once the server is running, explore and test the endpoints directly in your browser:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## API Overview & Sample Requests

### 1. Check Health
```bash
curl -X GET http://localhost:8000/health
```
**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "AquaVigil Backend",
  "version": "1.0.0",
  "database": "connected",
  "model_status": "not_configured",
  "timestamp": "2026-10-22T13:56:08.390301Z"
}
```

### 2. Analyze a Fish Image
```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -F "file=@/path/to/fish_sample.jpg"
```
**Response (201 Created):**
```json
{
  "analysis_id": 1,
  "status": "model_not_configured",
  "predicted_class": null,
  "confidence": null,
  "image_dimensions": {
    "width": 640,
    "height": 480
  },
  "explanation_available": false,
  "bounding_boxes": null,
  "original_filename": "fish_sample.jpg",
  "file_size_bytes": 105420,
  "mime_type": "image/jpeg",
  "created_at": "2026-10-22T13:56:14.039837",
  "error_message": null
}
```

### 3. Retrieve Historical Analyses (Paginated)
```bash
curl -X GET "http://localhost:8000/api/v1/analyses?limit=10&offset=0"
```

### 4. Fetch Aggregate Statistics
```bash
curl -X GET http://localhost:8000/api/v1/analyses/stats
```
**Response (200 OK):**
```json
{
  "total_analyses": 24,
  "counts_by_status": {
    "completed": 20,
    "model_not_configured": 4
  },
  "counts_by_class": {
    "Ichthyophthiriasis (White Spot)": 14,
    "Healthy Fish": 6
  },
  "analyses_last_24h": 9
}
```

---

## Environment Configuration

Configuration is managed in `.env` using Pydantic Settings.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_NAME` | `"AquaVigil Backend"` | Application identifier |
| `DATABASE_URL` | `"sqlite:///./storage/aquavigil.db"` | SQLite for dev, PostgreSQL for staging |
| `STORAGE_DIR` | `"./storage/uploads"` | Location where images are stored |
| `MAX_UPLOAD_SIZE_MB` | `10` | Maximum upload size in megabytes |
| `CORS_ORIGINS` | `"http://localhost:3000,http://127.0.0.1:3000..."` | Allowed web and mobile origins |
| `ENABLE_MOCK_MODEL` | `false` | Enable simulated predictions for UI testing |
| `MODEL_WEIGHTS_PATH` | `""` | File path to AI model weights |

---

## Troubleshooting Common Issues

### 1. `ModuleNotFoundError: No module named 'fastapi'`
- **Cause**: Virtual environment is not activated or dependencies were not installed.
- **Fix**: Run `source .venv/bin/activate` (or `.venv\Scripts\Activate.ps1` on Windows) and run `pip install -r requirements.txt`.

### 2. Mobile App or Frontend cannot connect (`Network Error` / `Connection Refused`)
- **Cause**: Mobile app or emulator is attempting to call `http://localhost:8000`.
- **Fix**:
  - Android Emulator: Connect to `http://10.0.2.2:8000`.
  - Physical Phone on Wi-Fi: Connect to host machine's LAN IP (e.g. `http://192.168.1.50:8000`).
  - Verify your IP is added to `CORS_ORIGINS` in `.env`.

### 3. File upload returns `HTTP 413 Content Too Large`
- **Cause**: Uploaded image exceeds `MAX_UPLOAD_SIZE_MB` (default 10 MB).
- **Fix**: Compress the image before uploading or increase `MAX_UPLOAD_SIZE_MB` in `.env`.

### 4. File upload returns `HTTP 400 The uploaded file is corrupted`
- **Cause**: Uploaded file is a text or binary file renamed with an image extension.
- **Fix**: AquaVigil uses Pillow magic-byte inspection. Ensure the file is an actual JPEG or PNG image.

---

## Teammate Handover Documentation

- **For Frontend & Mobile Developers**: See [FRONTEND_INTEGRATION.md](file:///Users/vishvanth/Downloads/AquaVigil/FRONTEND_INTEGRATION.md)
- **For AI/ML Model Developers**: See [AI_MODEL_INTEGRATION.md](file:///Users/vishvanth/Downloads/AquaVigil/AI_MODEL_INTEGRATION.md)
- **Detailed API Reference**: See [API_DOCUMENTATION.md](file:///Users/vishvanth/Downloads/AquaVigil/API_DOCUMENTATION.md)
- **Handover Checklist**: See [HANDOVER_CHECKLIST.md](file:///Users/vishvanth/Downloads/AquaVigil/HANDOVER_CHECKLIST.md)
