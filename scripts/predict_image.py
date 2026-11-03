"""Run a local detection checkpoint and export reviewable image predictions."""

import argparse
from contextlib import redirect_stdout
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError


class PredictionError(ValueError):
    """Describe invalid input or an unusable prediction."""


def file_hash(path):
    """Identify exact bytes without retaining the file in memory."""
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def probability(value, name):
    """Validate a configurable inference parameter, not a quality target."""
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise PredictionError(f"{name} debe estar entre 0 y 1")
    return value


def read_image(path):
    """Normalize EXIF orientation and transparency before inference."""
    try:
        with Image.open(path) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGBA")
            background = Image.new("RGBA", image.size, "white")
            return Image.alpha_composite(background, image).convert("RGB")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise PredictionError("No se puede leer la imagen") from exc


def predict_with_yolo(checkpoint, image, *, confidence, iou, image_size):
    """Load only an existing local checkpoint; never substitute pretrained weights."""
    os.environ.setdefault("YOLO_CONFIG_DIR", str(Path(__file__).resolve().parents[1] / "local-artifacts/ultralytics"))
    os.environ.setdefault("YOLO_OFFLINE", "true")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise PredictionError("Faltan las dependencias de requirements-inference.txt") from exc
    model = YOLO(str(checkpoint), task="detect")
    if model.task != "detect":
        raise PredictionError("El checkpoint no es de detección de objetos")
    result = model.predict(
        source=image, device="cpu", imgsz=image_size, conf=confidence,
        iou=iou, max_det=300, save=False, verbose=False,
    )[0]
    boxes = []
    if result.boxes is not None:
        for xyxy, class_id, score in zip(
            result.boxes.xyxy.cpu().tolist(), result.boxes.cls.cpu().tolist(),
            result.boxes.conf.cpu().tolist(), strict=True,
        ):
            boxes.append({"bbox_xyxy": xyxy, "class_id": class_id, "confidence": score})
    return dict(model.names), boxes


def normalize_detections(names, boxes, size):
    """Check model outputs in the EXIF-normalized original image coordinates."""
    width, height = size
    names = {int(key): str(value) for key, value in names.items()}
    detections = []
    for index, box in enumerate(boxes):
        class_number = float(box["class_id"])
        if not math.isfinite(class_number) or not class_number.is_integer() or int(class_number) not in names:
            raise PredictionError("El modelo devolvió una clase inválida")
        class_id = int(class_number)
        coordinates = [float(value) for value in box["bbox_xyxy"]]
        if len(coordinates) != 4 or not all(math.isfinite(value) for value in coordinates):
            raise PredictionError("El modelo devolvió coordenadas inválidas")
        x1, y1, x2, y2 = coordinates
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise PredictionError("Una caja está fuera de la imagen o tiene área cero")
        detections.append({
            "detection_id": index + 1, "class_id": class_id, "class_name": names[class_id],
            "confidence": probability(box["confidence"], "Confianza"),
            "bbox_xyxy": coordinates, "evidence_status": "unreviewed", "support": "unknown",
        })
    return names, detections


def draw_predictions(image, detections, confidence):
    """Draw candidate boxes with labels below and an explicit review notice."""
    header, footer = 38, 32
    font = ImageFont.load_default(size=16)
    measure = ImageDraw.Draw(image)
    placements = []
    for detection in detections:
        x1, _, _, y2 = detection["bbox_xyxy"]
        label = f"{detection['detection_id']}: {detection['class_name']} {100 * detection['confidence']:.1f}% [revisar]"
        while len(label) > 1 and measure.textlength(label, font=font) + 8 > image.width:
            label = label[:-2] + "~"
        label_width = min(image.width, int(measure.textlength(label, font=font)) + 8)
        left = min(int(x1), max(0, image.width - label_width))
        top = int(y2) + header + 2
        while any(left < right and left + label_width > other_left and top < bottom and top + 23 > other_top for other_left, other_top, right, bottom, _ in placements):
            top += 24
        placements.append((left, top, left + label_width, top + 23, label))
        footer = max(footer, top + 25 - image.height - header)
    canvas = Image.new("RGB", (image.width, image.height + header + footer), "#17202b")
    canvas.paste(image, (0, header))
    draw = ImageDraw.Draw(canvas)
    text = f"Predicciones sin revisar | umbral {confidence:g} | sin medicion de exposicion"
    if not detections:
        text = f"Sin detecciones con umbral {confidence:g} | no demuestra ausencia de logos"
    draw.text((6, 8), text, font=font, fill="white")
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox_xyxy"]
        left, top = min(x1, image.width - 1), min(y1, image.height - 1) + header
        draw.rectangle((left, top, min(x2, image.width - 1), min(y2, image.height - 1) + header), outline="#ffb347", width=3)
        draw.text((left + 3, top + 3), str(detection["detection_id"]), font=font, fill="#ffcf87", stroke_width=1, stroke_fill="#17202b")
    for left, top, right, bottom, label in placements:
        draw.rectangle((left, top, right, bottom), fill="#17202b")
        draw.text((left + 3, top + 2), label, font=font, fill="#ffcf87")
    return canvas


def package_versions():
    """Record installed runtime versions without importing the model backend."""
    values = {}
    for name in ("ultralytics", "torch", "torchvision", "Pillow", "numpy"):
        try:
            values[name] = version(name)
        except PackageNotFoundError:
            values[name] = None
    return values


def run_inference(image_path, checkpoint, output, *, confidence, iou=.7, image_size=640, predictor=predict_with_yolo):
    """Publish a complete report atomically, without overwriting source material."""
    image_path, checkpoint, output = Path(image_path).resolve(), Path(checkpoint).resolve(), Path(output).resolve()
    confidence = probability(confidence, "Umbral de confianza")
    iou = probability(iou, "IoU de supresión")
    if isinstance(image_size, bool) or not isinstance(image_size, int) or image_size < 32 or image_size % 32:
        raise PredictionError("imgsz debe ser un entero positivo múltiplo de 32")
    if not checkpoint.is_file() or checkpoint.suffix.lower() != ".pt":
        raise PredictionError("Indica un checkpoint .pt local existente")
    if output.exists():
        raise FileExistsError("La carpeta de salida ya existe; elige otra")
    if output == image_path or output == checkpoint or output in image_path.parents or output in checkpoint.parents:
        raise PredictionError("La salida no puede contener los archivos de entrada")
    image = read_image(image_path)
    input_hash, checkpoint_hash = file_hash(image_path), file_hash(checkpoint)
    start = time.perf_counter()
    with redirect_stdout(sys.stderr):
        names, boxes = predictor(checkpoint, image, confidence=confidence, iou=iou, image_size=image_size)
    elapsed = time.perf_counter() - start
    names, detections = normalize_detections(names, boxes, image.size)
    if file_hash(image_path) != input_hash or file_hash(checkpoint) != checkpoint_hash:
        raise PredictionError("La imagen o el checkpoint cambiaron durante la ejecución")
    report = {
        "schema_version": 1, "complete": True, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "image": {"filename": image_path.name, "sha256": input_hash, "width": image.width, "height": image.height, "orientation": "exif_transposed", "alpha_background": "white"},
        "model": {"filename": checkpoint.name, "sha256": checkpoint_hash, "class_names": names},
        "parameters": {"confidence": confidence, "iou": iou, "image_size": image_size, "device": "cpu", "max_detections": 300},
        "coordinate_system": "xyxy in original image after EXIF orientation; no header offset",
        "rendering": {"header_pixels": 38, "footer_pixels": 32, "file": "annotated.png"},
        "elapsed_model_seconds": elapsed, "python": sys.version, "versions": package_versions(),
        "detection_count": len(detections), "detections": detections,
        "limitations": ["Confidence is not measured accuracy or a clarity classification", "Unreviewed predictions do not establish brand exposure", "No detections does not establish that the logo is absent"],
    }
    rendered = draw_predictions(image, detections, confidence)
    report["rendering"]["footer_pixels"] = rendered.height - image.height - 38
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prediction-", dir=output.parent) as temporary:
        staged = Path(temporary) / "result"
        staged.mkdir()
        rendered.save(staged / "annotated.png")
        (staged / "predictions.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        with (staged / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = ["image_sha256", "checkpoint_sha256", "detection_id", "class_id", "class_name", "confidence", "x1", "y1", "x2", "y2", "evidence_status", "support"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for detection in detections:
                row = {key: value for key, value in detection.items() if key != "bbox_xyxy"}
                row.update(zip(("x1", "y1", "x2", "y2"), detection["bbox_xyxy"], strict=True))
                writer.writerow(dict(image_sha256=input_hash, checkpoint_sha256=checkpoint_hash, **row))
        staged.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description="Detectar logos en una imagen con un checkpoint local")
    parser.add_argument("image", type=Path)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confidence", type=float, required=True)
    parser.add_argument("--iou", type=float, default=.7)
    parser.add_argument("--image-size", type=int, default=640)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if not any(output.is_relative_to(root / folder) for folder in ("data/review", "local-artifacts")):
        parser.error("La salida debe quedar en data/review/ o local-artifacts/, excluidos de Git")
    try:
        result = run_inference(args.image, args.checkpoint, output, confidence=args.confidence, iou=args.iou, image_size=args.image_size)
    except (PredictionError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Error de inferencia: {exc}\n")
    print(json.dumps({"complete": True, "detections": result["detection_count"], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
