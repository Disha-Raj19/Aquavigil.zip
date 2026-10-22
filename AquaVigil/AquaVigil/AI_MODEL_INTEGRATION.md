# AquaVigil AI/ML Model Integration Specification

**Audience:** AI / Machine Learning Teammate  
**Backend Contact:** Python Backend Engineer  
**Integration Target File:** [`app/services/prediction_service.py`](file:///Users/vishvanth/Downloads/AquaVigil/app/services/prediction_service.py)

---

## 1. Executive Summary

The AquaVigil backend architecture is completely modularized and decoupled from the specific deep learning framework. The REST API routes, image validation, storage, and database persistence are fully operational and verified by automated tests.

When an image is uploaded:
1. It is validated and converted into a standard 3-channel **RGB `PIL.Image.Image`**.
2. It is passed directly to the `prediction_engine.predict(image)` method.
3. The result is serialized and returned to the frontend.

**Our Core Agreement:**  
The backend will **never fake disease predictions or invent confidence scores**. Until you deliver your trained model weights and class labels, the API returns `status: "model_not_configured"`. Once you deliver your weights, we only need to plug in your inference code inside `app/services/prediction_service.py`.

---

## 2. Information Required from the ML Teammate

Please fill out or confirm the following specifications:

| Requirement | Description | Your Specification |
| :--- | :--- | :--- |
| **Framework & Version** | e.g. PyTorch 2.2+, Ultralytics YOLOv8/v11, ONNX Runtime | ____________________ |
| **Model Architecture** | e.g. ResNet50, EfficientNet-B4, YOLOv8x-cls, ConvNeXt | ____________________ |
| **Model Weights File** | File name and format (e.g. `best.pt`, `model.onnx`, `weights.pth`) | ____________________ |
| **Input Resolution** | Pixel dimensions (e.g. $224 \times 224$, $384 \times 384$, $640 \times 640$) | ____________________ |
| **Normalization Constants** | Mean and Std per RGB channel (e.g. ImageNet defaults) | ____________________ |
| **Class Label List** | Exact list of disease classes in index order | ____________________ |
| **Confidence Metric** | Multi-class Softmax probability or Multi-label Sigmoid | ____________________ |
| **Detection Bounding Boxes** | Is your model classification-only or object detection? | ____________________ |
| **Explainability (XAI)** | Do you support Grad-CAM, Eigen-CAM, or feature maps? | ____________________ |
| **Target Hardware** | CPU inference or CUDA/GPU required? | ____________________ |

---

## 3. Input Contract (`predict(image)`)

The backend passes a clean, in-memory PIL image:
- **Type:** `PIL.Image.Image`
- **Color Mode:** `"RGB"` (Always 3 channels, guaranteed)
- **Dimensions:** Variable original dimensions (e.g., $1920 \times 1080$, $640 \times 480$). **Your preprocessing transform must resize/crop as required by your model.**

---

## 4. Output Contract (`PredictionResult`)

Your model inference must return an instance of `PredictionResult`:

```python
from app.services.prediction_service import PredictionResult

result = PredictionResult(
    status="completed",                     # Must be "completed" or "failed"
    predicted_class="White Spot Disease",   # String: diagnosed condition name
    confidence=0.942,                       # Float between 0.0 and 1.0
    bounding_boxes=[                        # Optional: list of lesion bounding boxes
        {
            "box": [ymin, xmin, ymax, xmax], # or [x1, y1, x2, y2]
            "label": "White Spot Lesion",
            "confidence": 0.942
        }
    ],
    explanation_available=True,             # Set to True if Grad-CAM was computed
    explanation_metadata={                  # Optional metadata for Grad-CAM
        "method": "Grad-CAM",
        "target_layer": "layer4",
        "heatmap_resolution": "224x224"
    },
    error_message=None
)
```

---

## 5. Step-by-Step Integration Guide

### Step 1: Save Model Weights
Place your trained weights file into a local folder:
```bash
mkdir -p storage/weights
cp /path/to/your/trained_model.pt storage/weights/fish_disease_v1.pt
```

### Step 2: Configure Environment Variable
In `.env`, set:
```bash
MODEL_WEIGHTS_PATH="./storage/weights/fish_disease_v1.pt"
MODEL_DEVICE="cpu"  # or "cuda" if GPU is available
```

### Step 3: Implement Inference in `app/services/prediction_service.py`

Below is the turnkey integration template already set up in [`app/services/prediction_service.py`](file:///Users/vishvanth/Downloads/AquaVigil/app/services/prediction_service.py):

```python
import torch
from torchvision import transforms
from PIL import Image
from app.services.prediction_service import BasePredictionEngine, PredictionResult

class FishDiseasePyTorchEngine(BasePredictionEngine):
    def __init__(self, weights_path: str, device: str = "cpu"):
        self.device = torch.device(device)
        self.weights_path = weights_path
        
        # 1. Define disease classes in order of output logits
        self.classes = [
            "Healthy Fish",
            "Ichthyophthiriasis (White Spot)",
            "Columnaris (Cotton Wool Disease)",
            "Fin and Tail Rot",
            "Epizootic Ulcerative Syndrome (EUS)",
            "Saprolegniasis (Fungal Infection)",
        ]
        
        # 2. Define standard inference transform
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        # 3. Load model architecture & weights
        self._load_model()

    def _load_model(self):
        # Example loading PyTorch model
        # from torchvision.models import efficientnet_b0
        # self.model = efficientnet_b0(num_classes=len(self.classes))
        # state_dict = torch.load(self.weights_path, map_location=self.device)
        # self.model.load_state_dict(state_dict)
        # self.model.to(self.device)
        # self.model.eval()
        pass

    def predict(self, image: Image.Image) -> PredictionResult:
        try:
            tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                logits = self.model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                top_prob, top_idx = torch.max(probs, dim=0)

            predicted_label = self.classes[top_idx.item()]
            confidence = round(top_prob.item(), 4)

            return PredictionResult(
                status="completed",
                predicted_class=predicted_label,
                confidence=confidence,
                explanation_available=False,
            )
        except Exception as exc:
            return PredictionResult(
                status="failed",
                predicted_class=None,
                confidence=None,
                error_message=f"Model inference failed: {str(exc)}"
            )

    def is_ready(self) -> bool:
        return hasattr(self, "model") and self.model is not None

    def get_status_label(self) -> str:
        return "ready" if self.is_ready() else "not_configured"
```

---

## 6. Explainable AI (Grad-CAM) Guidelines

If your model supports Grad-CAM:
1. Hook into the final convolutional feature layer (e.g. `model.features[-1]` or `layer4`).
2. Generate the normalized heatmap overlay ($[0.0, 1.0]$ floating array).
3. If you want the backend to store the generated heatmap image, save it to `storage/uploads/gradcam_<analysis_id>.png` and populate `explanation_available=True` and `explanation_path`.
4. The backend already provides a dedicated endpoint `GET /api/v1/analyses/{analysis_id}/explanation` to deliver this metadata to the Flutter app and Next.js dashboard.

---

## 7. Sample Integration Test

To verify your model integration without starting the full frontend:
```bash
python -c "
from PIL import Image
from app.services.prediction_service import get_prediction_engine

engine = get_prediction_engine()
img = Image.new('RGB', (224, 224), color=(0, 128, 255))
result = engine.predict(img)
print('Inference Status:', result.status)
print('Predicted Class :', result.predicted_class)
print('Confidence Score:', result.confidence)
"
```
