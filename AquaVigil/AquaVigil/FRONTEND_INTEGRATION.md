# AquaVigil Frontend & Mobile Integration Guide

**Audience:** Flutter Mobile Developer & Next.js Web Dashboard Developer  
**Backend Contact:** Python Backend Engineer  
**API Base URL:**
- Web Localhost: `http://localhost:8000`
- Android Emulator: `http://10.0.2.2:8000`
- iOS Simulator: `http://localhost:8000`
- Physical Phone over Wi-Fi: `http://<YOUR_COMPUTER_LAN_IP>:8000` (e.g. `http://192.168.1.45:8000`)

---

## 1. Network & Connection Essentials

### Why `localhost` Does Not Work on Mobile Devices

- **Android Emulator**: The Android emulator runs inside a virtual router. In the emulator, `localhost` (or `127.0.0.1`) refers to the **emulator phone itself**, NOT your laptop/development computer. You must use `http://10.0.2.2:8000` to reach your laptop's backend.
- **Physical Mobile Devices**: A phone connected via USB or Wi-Fi is a separate device on your local network. It cannot access `localhost`. Find your laptop's LAN IP address:
  - macOS / Linux: Run `ifconfig` or `ip a` (look for `en0` or `wlan0`, e.g., `192.168.1.45`).
  - Windows: Run `ipconfig` (look for `IPv4 Address`).
  - Use `http://192.168.1.45:8000` in your Flutter code.
  - **Important:** Add your LAN IP to the `CORS_ORIGINS` in `.env` if testing Flutter Web or Next.js across devices.

### CORS Configuration

The backend explicitly restricts Cross-Origin Resource Sharing for security. The default allowed origins are defined in `.env`:
```bash
CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8081,http://10.0.2.2:8000"
```
If your frontend runs on another port or host, append it to `CORS_ORIGINS` in `.env` separated by commas.

---

## 2. API Endpoints Quick Reference

| Action | Method | Path | Request Body / Query |
| :--- | :--- | :--- | :--- |
| **Health Check** | `GET` | `/health` | None |
| **Analyze Image** | `POST` | `/api/v1/analyses` | `multipart/form-data`, field: `file` |
| **Get History** | `GET` | `/api/v1/analyses` | `?limit=10&offset=0` |
| **Get Analysis** | `GET` | `/api/v1/analyses/{id}`| None |
| **Get Explanation** | `GET` | `/api/v1/analyses/{id}/explanation` | None |
| **Stream Image** | `GET` | `/api/v1/analyses/{id}/image` | None |
| **Delete Analysis** | `DELETE`| `/api/v1/analyses/{id}` | None |
| **Dashboard Stats** | `GET` | `/api/v1/analyses/stats` | None |

---

## 3. Image Upload Specifications

- **HTTP Method:** `POST`
- **Endpoint:** `/api/v1/analyses`
- **Header:** `Content-Type: multipart/form-data`
- **Field Name:** `file` *(Must be named `file` exactly)*
- **Accepted File Types:** `.jpg`, `.jpeg`, `.png`
- **Max File Size:** 10 MB

### Understanding the Response `status` Field

Your UI must inspect the `status` field in the response:

1. `"completed"`: AI inference succeeded. `predicted_class` contains the disease name, and `confidence` contains the score (0.0 to 1.0).
2. `"model_not_configured"`: The backend received and stored the image, but the ML teammate has not yet plugged in the AI weights. `predicted_class` and `confidence` are `null`. **Display a message such as: "Image recorded — AI model awaiting weights."**
3. `"failed"`: Model inference failed or image was uninterpretable. Check `error_message`.

---

## 4. Flutter Integration (Dart)

### Required Dependencies (`pubspec.yaml`)
```yaml
dependencies:
  http: ^1.2.0
  image_picker: ^1.0.7
```

### Complete Flutter Service Implementation

```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

class AquaVigilApiService {
  // Use 10.0.2.2 for Android emulator, or your LAN IP for physical device
  static const String baseUrl = Platform.isAndroid 
      ? 'http://10.0.2.2:8000' 
      : 'http://localhost:8000';

  /// Upload fish image for diagnosis
  Future<Map<String, dynamic>> uploadFishImage(File imageFile) async {
    final uri = Uri.parse('$baseUrl/api/v1/analyses');
    final request = http.MultipartRequest('POST', uri);

    // Attach image using the required field name 'file'
    request.files.add(
      await http.MultipartFile.fromPath(
        'file',
        imageFile.path,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 201) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['detail'] ?? 'Failed to analyze fish image');
    }
  }

  /// Fetch analysis history with pagination
  Future<Map<String, dynamic>> fetchHistory({int limit = 10, int offset = 0}) async {
    final uri = Uri.parse('$baseUrl/api/v1/analyses?limit=$limit&offset=$offset');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load history');
    }
  }

  /// Fetch aggregate dashboard statistics
  Future<Map<String, dynamic>> fetchStatistics() async {
    final uri = Uri.parse('$baseUrl/api/v1/analyses/stats');
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load statistics');
    }
  }
}
```

---

## 5. Next.js Web Dashboard Integration (TypeScript)

### Type Definitions (`types/aquavigil.ts`)

```typescript
export interface ImageDimensions {
  width: number;
  height: number;
}

export interface BoundingBox {
  box: [number, number, number, number];
  label: string;
  confidence: number;
}

export interface AnalysisRecord {
  analysis_id: number;
  status: "completed" | "model_not_configured" | "failed" | "pending";
  predicted_class: string | null;
  confidence: number | null;
  image_dimensions: ImageDimensions | null;
  explanation_available: boolean;
  bounding_boxes: BoundingBox[] | null;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  created_at: string;
  error_message: string | null;
}

export interface StatisticsResponse {
  total_analyses: number;
  counts_by_status: Record<string, number>;
  counts_by_class: Record<string, number>;
  analyses_last_24h: number;
}
```

### Complete API Client (`lib/api.ts`)

```typescript
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Upload a fish image file to the AquaVigil backend
 */
export async function analyzeFishImage(file: File): Promise<AnalysisRecord> {
  const formData = new FormData();
  // Field name MUST be 'file'
  formData.append("file", file);

  const response = await fetch(`${BACKEND_URL}/api/v1/analyses`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch paginated analysis history
 */
export async function getAnalyses(limit = 10, offset = 0): Promise<{
  total: number;
  limit: number;
  offset: number;
  items: AnalysisRecord[];
}> {
  const res = await fetch(`${BACKEND_URL}/api/v1/analyses?limit=${limit}&offset=${offset}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch analyses");
  return res.json();
}

/**
 * Fetch dashboard statistics
 */
export async function getStatistics(): Promise<StatisticsResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/analyses/stats`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch statistics");
  return res.json();
}
```

### React Upload Component Example (`components/FishUploader.tsx`)

```tsx
"use client";

import React, { useState } from "react";
import { analyzeFishImage, AnalysisRecord } from "../lib/api";

export default function FishUploader() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyzeFishImage(selectedFile);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-lg mx-auto bg-white rounded-xl shadow-md space-y-4">
      <h2 className="text-xl font-bold">AquaVigil Fish Diagnosis</h2>
      <input
        type="file"
        accept="image/jpeg,image/png"
        onChange={handleFileChange}
        disabled={loading}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />

      {loading && <p className="text-blue-500 font-medium">Processing fish image...</p>}
      {error && <p className="text-red-500 font-medium">{error}</p>}

      {result && (
        <div className="p-4 border rounded bg-gray-50 space-y-2">
          <p><strong>Analysis ID:</strong> {result.analysis_id}</p>
          <p><strong>Status:</strong> {result.status}</p>
          {result.status === "completed" ? (
            <>
              <p><strong>Predicted Disease:</strong> {result.predicted_class}</p>
              <p><strong>Confidence:</strong> {((result.confidence ?? 0) * 100).toFixed(1)}%</p>
            </>
          ) : result.status === "model_not_configured" ? (
            <p className="text-amber-600">
              Image saved successfully. AI model weights are awaiting integration.
            </p>
          ) : (
            <p className="text-red-600">Error: {result.error_message}</p>
          )}
        </div>
      )}
    </div>
  );
}
```
