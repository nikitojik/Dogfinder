import io
import logging
from functools import lru_cache

import numpy as np
import open_clip
import torch
from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)

CLIP_MODEL = "ViT-B-32"
CLIP_PRETRAINED = "laion2b_s34b_b79k"
YOLO_WEIGHTS = "yolov8n.pt"

EMBEDDING_DIM = 512
MIN_BOX_RATIO = 0.05
BOX_PADDING = 0.08


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class Embedder:
    def __init__(self) -> None:
        self.device = pick_device()
        logger.info("Загружаем модели на %s", self.device)

        self.detector = YOLO(YOLO_WEIGHTS)

        model, _, preprocess = open_clip.create_model_and_transforms(
            CLIP_MODEL, pretrained=CLIP_PRETRAINED
        )
        self.model = model.to(self.device).eval()
        self.preprocess = preprocess

        logger.info("Модели загружены")

    def detect_dog(self, image: Image.Image) -> tuple[float, float, float, float] | None:
        result = self.detector(image, verbose=False)[0]

        best_box = None
        best_conf = 0.0

        for box in result.boxes:
            if result.names[int(box.cls)] != "dog":
                continue
            conf = float(box.conf)
            if conf > best_conf:
                best_conf = conf
                best_box = box.xyxy[0].tolist()

        if best_box is None:
            return None

        x1, y1, x2, y2 = best_box
        width, height = image.size

        if ((x2 - x1) * (y2 - y1)) / (width * height) < MIN_BOX_RATIO:
            return None

        return x1, y1, x2, y2

    def crop(self, image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
        x1, y1, x2, y2 = box
        width, height = image.size

        pad_x = (x2 - x1) * BOX_PADDING
        pad_y = (y2 - y1) * BOX_PADDING

        return image.crop(
            (
                max(0, x1 - pad_x),
                max(0, y1 - pad_y),
                min(width, x2 + pad_x),
                min(height, y2 + pad_y),
            )
        )

    def encode(self, image: Image.Image) -> np.ndarray:
        tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy()[0].astype(np.float32)

    def process(self, image_bytes: bytes) -> dict:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        box = self.detect_dog(image)
        target = self.crop(image, box) if box else image

        return {
            "embedding": self.encode(target),
            "box": list(box) if box else None,
            "dog_detected": box is not None,
        }


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
