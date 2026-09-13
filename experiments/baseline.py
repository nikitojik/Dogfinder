import sys
from collections import defaultdict
from pathlib import Path

import open_clip
import torch
from PIL import Image

DATA_DIR = Path(__file__).parent / "data"
MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_model(device: str):
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
    model = model.to(device).eval()
    return model, preprocess


def embed_images(paths: list[Path], model, preprocess, device: str) -> torch.Tensor:
    tensors = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        tensors.append(preprocess(image))

    batch = torch.stack(tensors).to(device)

    with torch.no_grad():
        features = model.encode_image(batch)
        features = features / features.norm(dim=-1, keepdim=True)

    return features.cpu()


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
    paths = sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    if not paths:
        print(f"Положи фотографии в {DATA_DIR}")
        sys.exit(1)

    ids = [dog_id(p) for p in paths]

    groups = defaultdict(list)
    for path, identifier in zip(paths, ids, strict=True):
        groups[identifier].append(path)

    singles = [key for key, value in groups.items() if len(value) < 2]
    if singles:
        print(f"У этих собак только одно фото, они портят метрику: {singles}")

    print(f"Фотографий: {len(paths)}, собак: {len(groups)}")

    device = pick_device()
    print(f"Устройство: {device}")

    model, preprocess = load_model(device)
    features = embed_images(paths, model, preprocess, device)

    print(f"Размерность эмбеддинга: {features.shape[1]}")
    print()

    for k in (1, 5, 10):
        value = recall_at_k(features, ids, k)
        print(f"Recall@{k}: {value:.3f}")


if __name__ == "__main__":
    main()
