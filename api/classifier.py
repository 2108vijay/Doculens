"""
api/classifier.py — MobileNetV2 inference
"""
import io, os
from pathlib import Path
import torch
import torch.nn.functional as F
from torchvision import models, transforms
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

CLASSES   = ["aadhaar", "pan", "other"]
IMG_SIZE  = 224
THRESHOLD = 0.60
MODEL_PATH = Path(os.getenv("MODEL_PATH", "best_model.pth"))

TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


class Classifier:
    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at '{MODEL_PATH}'")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = models.mobilenet_v2(weights=None)
        self.model.classifier = torch.nn.Sequential(
            torch.nn.Dropout(0.2),
            torch.nn.Linear(self.model.last_channel, len(CLASSES)),
        )
        state = torch.load(MODEL_PATH, map_location=self.device)
        if isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()
        print(f"✅ Classifier ready on {self.device}")

    def predict(self, image_bytes: bytes) -> dict:
        image  = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        tensor = TRANSFORM(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            probs = F.softmax(self.model(tensor), dim=1)[0]
        pred_idx   = int(probs.argmax())
        confidence = float(probs[pred_idx])
        return {
            "classification": CLASSES[pred_idx],
            "confidence":     confidence,
            "probabilities":  {
                "aadhaar": float(probs[0]),
                "pan":     float(probs[1]),
                "other":   float(probs[2]),
            },
            "is_uncertain": confidence < THRESHOLD,
        }


_classifier: Classifier = None

def get_classifier() -> Classifier:
    global _classifier
    if _classifier is None:
        _classifier = Classifier()
    return _classifier
