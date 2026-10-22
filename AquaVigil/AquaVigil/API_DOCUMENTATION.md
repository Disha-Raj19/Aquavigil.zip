# AquaVigil REST API Documentation

**API Version:** `1.0.0`  
**Base URL:** `http://localhost:8000` (or `http://<LAN_IP>:8000`)  
**Prefix:** `/api/v1`

---

## Table of Contents

1. [Overview & Conventions](#overview--conventions)
2. [Status Codes & Error Responses](#status-codes--error-responses)
3. [Endpoints](#endpoints)
   - [1. Service Health Check](#1-service-health-check)
   - [2. Analyze Fish Image](#2-analyze-fish-image)
   - [3. List Analysis History](#3-list-analysis-history)
   - [4. Get Single Analysis](#4-get-single-analysis)
   - [5. Get Analysis Explanation (XAI)](#5-get-analysis-explanation-xai)
   - [6. Stream Analysis Image](#6-stream-analysis-image)
   - [7. Delete Analysis Record](#7-delete-analysis-record)
   - [8. Aggregate Statistics](#8-aggregate-statistics)
4. [Data Schemas](#data-schemas)

---

## Overview & Conventions

- **Data Format**: All JSON responses use standard camelCase or snake_case as specified in schemas.
- **Timestamps**: Serialized as ISO-8601 strings in UTC (e.g. `2026-10-22T13:56:14.039837Z`).
- **Security Notice**: This initial API is intended for collegiate prototype integration and local development. It does not enforce user authentication or rate limits. Do not expose this service directly to the public internet without an API gateway or reverse proxy with TLS and authentication.

---

## Status Codes & Error Responses

| Status Code | Meaning | Reason |
| :--- | :--- | :--- |
| `200 OK` | Success | Request succeeded. |
| `201 Created` | Created | Image uploaded, analyzed, and stored. |
| `400 Bad Request` | Client Error | Empty file, corrupted image, or missing file parameter. |
| `404 Not Found` | Not Found | Requested `analysis_id` does not exist. |
| `409 Conflict` | Conflict | Explanation requested for an analysis where XAI is unavailable. |
| `413 Content Too Large` | Payload Too Large | File size exceeds configured ceiling (10 MB). |
| `415 Unsupported Media`| Unsupported Format| Upload is not a JPEG or PNG image. |
| `500 Server Error` | Internal Error | Unhandled runtime exception. |

### Standard Error Response Format
```json
{
  "detail": "Description of the error condition."
}
```

---

## Endpoints

### 1. Service Health Check

Returns API readiness, database connection state, and ML model status.

- **Method:** `GET`
- **Paths:** `/health`, `/api/v1/health`
- **Auth:** None

#### Response (200 OK)
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

---

### 2. Analyze Fish Image

Accepts a multipart file upload, validates format and integrity, converts to RGB, saves to storage, and executes computer vision inference.

- **Method:** `POST`
- **Path:** `/api/v1/analyses`
- **Content-Type:** `multipart/form-data`
- **Form Field Name:** `file` (Required)
- **Supported Formats:** JPEG, JPG, PNG
- **Max File Size:** 10 MB

#### cURL Example
```bash
curl -X POST http://localhost:8000/api/v1/analyses \
  -F "file=@/path/to/fish_sample.jpg"
```

#### Response (201 Created) — Model Awaiting Integration
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

#### Response (201 Created) — Real Model Connected
```json
{
  "analysis_id": 2,
  "status": "completed",
  "predicted_class": "Ichthyophthiriasis (White Spot)",
  "confidence": 0.942,
  "image_dimensions": {
    "width": 800,
    "height": 600
  },
  "explanation_available": true,
  "bounding_boxes": [
    {
      "box": [120.5, 85.0, 310.2, 290.4],
      "label": "White Spot Lesion",
      "confidence": 0.942
    }
  ],
  "original_filename": "tilapia_infected.jpg",
  "file_size_bytes": 245012,
  "mime_type": "image/jpeg",
  "created_at": "2026-10-22T14:10:02.115402",
  "error_message": null
}
```

---

### 3. List Analysis History

Retrieve historical analyses sorted in descending chronological order (newest first).

- **Method:** `GET`
- **Path:** `/api/v1/analyses`
- **Query Parameters:**
  - `limit` (integer, default: `10`, range: `1` to `100`): Maximum records to return.
  - `offset` (integer, default: `0`, min: `0`): Number of records to skip.

#### cURL Example
```bash
curl -X GET "http://localhost:8000/api/v1/analyses?limit=5&offset=0"
```

#### Response (200 OK)
```json
{
  "total": 35,
  "limit": 5,
  "offset": 0,
  "items": [
    {
      "analysis_id": 35,
      "status": "completed",
      "predicted_class": "Healthy Fish",
      "confidence": 0.98,
      "image_dimensions": {
        "width": 640,
        "height": 480
      },
      "explanation_available": false,
      "bounding_boxes": null,
      "original_filename": "carp_healthy.png",
      "file_size_bytes": 142080,
      "mime_type": "image/png",
      "created_at": "2026-10-22T14:30:00.000000",
      "error_message": null
    }
  ]
}
```

---

### 4. Get Single Analysis

Retrieve complete details for a single analysis record by its identifier.

- **Method:** `GET`
- **Path:** `/api/v1/analyses/{analysis_id}`
- **Path Parameter:** `analysis_id` (integer)

#### cURL Example
```bash
curl -X GET http://localhost:8000/api/v1/analyses/1
```

#### Response (200 OK)
Same schema as single item from `POST /analyses`.

#### Error Response (404 Not Found)
```json
{
  "detail": "Analysis record with ID 999 was not found."
}
```

---

### 5. Get Analysis Explanation (XAI)

Retrieve Explainable AI (Grad-CAM or Saliency) metadata and heatmap links.

- **Method:** `GET`
- **Path:** `/api/v1/analyses/{analysis_id}/explanation`
- **Path Parameter:** `analysis_id` (integer)

#### Response (200 OK) — When Explanation is Available
```json
{
  "analysis_id": 2,
  "explanation_available": true,
  "method": "Grad-CAM",
  "metadata": {
    "target_layer": "model.features.stage4",
    "heatmap_resolution": "224x224"
  },
  "explanation_image_url": "/api/v1/analyses/2/explanation/image",
  "message": "Visual explanation metadata successfully retrieved."
}
```

#### Error Response (409 Conflict) — When Explanation was Not Generated
```json
{
  "detail": "No visual explanation (e.g., Grad-CAM) is available for analysis ID 1. Explanations require a trained model with feature attribution layers enabled."
}
```

---

### 6. Stream Analysis Image

Safely retrieve the stored image file without exposing server filesystem paths.

- **Method:** `GET`
- **Path:** `/api/v1/analyses/{analysis_id}/image`
- **Path Parameter:** `analysis_id` (integer)

#### Response (200 OK)
Binary image stream with `Content-Type: image/jpeg` or `image/png`.

---

### 7. Delete Analysis Record

Permanently removes the database record and cleans up the stored file from disk.

- **Method:** `DELETE`
- **Path:** `/api/v1/analyses/{analysis_id}`
- **Path Parameter:** `analysis_id` (integer)

#### cURL Example
```bash
curl -X DELETE http://localhost:8000/api/v1/analyses/1
```

#### Response (200 OK)
```json
{
  "analysis_id": 1,
  "message": "Analysis record 1 and associated image file were successfully deleted.",
  "success": true
}
```

---

### 8. Aggregate Statistics

Returns dashboard metrics across all historical analyses.

- **Method:** `GET`
- **Path:** `/api/v1/analyses/stats`

#### cURL Example
```bash
curl -X GET http://localhost:8000/api/v1/analyses/stats
```

#### Response (200 OK)
```json
{
  "total_analyses": 42,
  "counts_by_status": {
    "completed": 35,
    "model_not_configured": 5,
    "failed": 2
  },
  "counts_by_class": {
    "Ichthyophthiriasis (White Spot)": 18,
    "Healthy Fish": 12,
    "Fin Rot": 5
  },
  "analyses_last_24h": 11
}
```

---

## Data Schemas

### AnalysisResponse
```typescript
interface AnalysisResponse {
  analysis_id: number;
  status: "completed" | "model_not_configured" | "failed" | "pending";
  predicted_class: string | null;
  confidence: number | null; // Value between 0.0 and 1.0
  image_dimensions: {
    width: number;
    height: number;
  } | null;
  explanation_available: boolean;
  bounding_boxes: Array<{
    box: [number, number, number, number]; // [x1, y1, x2, y2]
    label: string;
    confidence: number;
  }> | null;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  created_at: string; // ISO 8601 UTC
  error_message: string | null;
}
```
