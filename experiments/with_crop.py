import sys
from pathlib import Path

import open_clip
import torch
from PIL import Image
from ultralytics import YOLO

DATA_DIR = Path(__file__).parent / "data"
CROPS_DIR = Path(__file__).parent / "crops"
SUFFIXES = {".jpg", ".jpeg", ".png"}

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"
YOLO_WEIGHTS = "yolov8n.pt"

MIN_BOX_RATIO = 0.05
BOX_PADDING = 0.08


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def crop_dog(image: Image.Image, detector: YOLO) -> tuple[Image.Image, bool]:
    result = detector(image, verbose=False)[0]

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
        return image, False

    x1, y1, x2, y2 = best_box
    width, height = image.size

    area_ratio = ((x2 - x1) * (y2 - y1)) / (width * height)
    if area_ratio < MIN_BOX_RATIO:
        return image, False

    pad_x = (x2 - x1) * BOX_PADDING
    pad_y = (y2 - y1) * BOX_PADDING

    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)

    return image.crop((x1, y1, x2, y2)), True


def dog_id(path: Path) -> str:
    return path.stem.split("_")[0]


def recall_at_k(features: torch.Tensor, ids: list[str], k: int) -> float:
    similarity = features @ features.T
    similarity.fill_diagonal_(-1.0)

    hits = 0
    for i in range(len(ids)):
        top_k = similarity[i].topk(k).indices.tolist()
        if any(ids[j] == ids[i] for j in top_k):
            hits += 1

    return hits / len(ids)


def main() -> None:
    paths = sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in SUFFIXES)
    if not paths:
        print(f"Положи фотографии в {DATA_DIR}")
        sys.exit(1)

    ids = [dog_id(p) for p in paths]
    device = pick_device()
    print(f"Фотографий: {len(paths)}, собак: {len(set(ids))}, устройство: {device}")

    detector = YOLO(YOLO_WEIGHTS)
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()

    CROPS_DIR.mkdir(exist_ok=True)

    tensors = []
    detected = 0

    for path in paths:
        image = Image.open(path).convert("RGB")
        cropped, found = crop_dog(image, detector)
        detected += found

        cropped.save(CROPS_DIR / f"{path.stem}.jpg", quality=90)
        tensors.append(preprocess(cropped))

    print(f"Собака найдена на {detected} из {len(paths)} фотографий")
    print()

    batch = torch.stack(tensors).to(device)
    with torch.no_grad():
        features = model.encode_image(batch)
        features = features / features.norm(dim=-1, keepdim=True)
    features = features.cpu()

    for k in (1, 5, 10):
        print(f"Recall@{k}: {recall_at_k(features, ids, k):.3f}")


if __name__ == "__main__":
    main()
