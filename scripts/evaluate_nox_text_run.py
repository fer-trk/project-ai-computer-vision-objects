"""Evaluate one NOX text checkpoint once on the reserved test images.

This wrapper reuses predict_image.run_inference for every image. It adds the
guards that make a single, reproducible evaluation possible and a manual review
step. It never measures exposure time or percentages and never reads confidence
as precision.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile

from predict_image import PredictionError, file_hash, predict_with_yolo, probability, run_inference

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CLASSES = {0: "nox_texto"}
RESERVED_SPLIT = "test"
OUTPUT_FOLDERS = ("data/review", "local-artifacts")
SYNTHETIC_FOLDER = "data-synthetic"
VERDICTS = ("true_positive", "false_positive")
FIXED_LIMITATIONS = [
    "Confidence is a model score, not measured precision or a clarity classification",
    "Counts come from manual review of the listed images only and are not a quality claim",
    "Detections do not establish brand exposure; no exposure time or percentage is computed",
    "No detections does not establish that the logo is absent",
]


class EvaluationError(PredictionError):
    """Describe a blocked or inconsistent evaluation."""


def read_class_names(checkpoint):
    """Read class names from a local checkpoint without running inference."""
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / "local-artifacts/ultralytics"))
    os.environ.setdefault("YOLO_OFFLINE", "true")
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise EvaluationError("Faltan las dependencias de requirements-inference.txt") from exc
    model = YOLO(str(checkpoint), task="detect")
    if model.task != "detect":
        raise EvaluationError("El checkpoint no es de detección de objetos")
    return dict(model.names)


def git_ignores(path, root):
    """Ask Git whether a path is ignored; unknown answers count as not ignored."""
    relative = Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    try:
        result = subprocess.run(["git", "check-ignore", "-q", "--", relative], cwd=root, capture_output=True)
    except OSError:
        return False
    return result.returncode == 0


def is_synthetic(path):
    """Detect any path inside the synthetic data folder."""
    return SYNTHETIC_FOLDER in (part.lower() for part in Path(path).resolve().parts)


def check_output_location(path, root, ignore_check):
    """Allow only Git-ignored review folders for outputs."""
    path, root = Path(path).resolve(), Path(root).resolve()
    if not any(path.is_relative_to(root / folder) for folder in OUTPUT_FOLDERS):
        raise EvaluationError("La salida debe quedar en data/review/ o local-artifacts/")
    if not ignore_check(path, root):
        raise EvaluationError("La salida no está ignorada por Git; no se publica nada")


def load_reserved_images(manifest_path, images_dir, names=None):
    """Select the reserved test images and block leaks, synthetic data and gaps."""
    manifest_path, images_dir = Path(manifest_path).resolve(), Path(images_dir).resolve()
    if is_synthetic(manifest_path) or is_synthetic(images_dir):
        raise EvaluationError("Las imágenes sintéticas de data-synthetic/ no pueden evaluarse")
    if not manifest_path.is_file() or not images_dir.is_dir():
        raise EvaluationError("Indica un manifiesto y una carpeta de imágenes existentes")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvaluationError("No se puede leer el manifiesto") from exc
    entries = manifest.get("images") if isinstance(manifest, dict) else None
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise EvaluationError("El manifiesto no contiene la lista images")
    classes = manifest.get("classes")
    if not isinstance(classes, dict) or {str(key): value for key, value in classes.items()} != {"0": "nox_texto"}:
        raise EvaluationError("El manifiesto no declara únicamente la clase 0: nox_texto")
    reserved = [entry for entry in entries if entry.get("split") == RESERVED_SPLIT]
    if not reserved:
        raise EvaluationError("El manifiesto no tiene una partición reservada 'test'")
    other_hashes = {entry.get("source_sha256") for entry in entries if entry.get("split") != RESERVED_SPLIT}
    if any(entry.get("source_sha256") in other_hashes for entry in reserved):
        raise EvaluationError("Una imagen reservada también aparece en train o val")
    if names is not None:
        by_name = {}
        for entry in reserved:
            by_name.setdefault(Path(str(entry.get("image"))).name, []).append(entry)
        if len(set(names)) != len(names):
            raise EvaluationError("La lista de imágenes tiene nombres repetidos")
        selected = []
        for name in names:
            if len(by_name.get(name, [])) != 1:
                raise EvaluationError(f"{name} no es una imagen única de la partición reservada")
            selected.append(by_name[name][0])
        reserved = selected
    items = []
    for entry in reserved:
        for field in ("image", "source_sha256"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise EvaluationError(f"Una imagen reservada no tiene {field}")
        for field in ("width", "height"):
            if isinstance(entry.get(field), bool) or not isinstance(entry.get(field), int) or entry[field] <= 0:
                raise EvaluationError(f"{entry['image']} no tiene {field} válido")
        if entry.get("synthetic"):
            raise EvaluationError(f"{entry['image']} está marcada como sintética")
        path = (images_dir / entry["image"]).resolve()
        if not path.is_relative_to(images_dir) or is_synthetic(path):
            raise EvaluationError(f"{entry['image']} queda fuera de la carpeta de imágenes o es sintética")
        if not path.is_file():
            raise EvaluationError(f"No existe la imagen reservada {entry['image']}")
        items.append({"entry": entry, "path": path})
    return manifest, items


def write_csv(path, fields, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_evaluation(
    *, checkpoint, images_dir, manifest, output, confidence, image_names=None, confidence_rationale=None,
    iou=.7, image_size=640, predictor=predict_with_yolo, class_reader=read_class_names,
    root=ROOT, ignore_check=git_ignores,
):
    """Run the checks, then one inference per reserved image, and publish atomically."""
    if confidence is None:
        raise EvaluationError("Indica --confidence; no existe un umbral por defecto")
    confidence = probability(confidence, "Umbral de confianza")
    checkpoint, images_dir, manifest_path, output = (Path(value).resolve() for value in (checkpoint, images_dir, manifest, output))
    if not checkpoint.is_file() or checkpoint.suffix.lower() != ".pt":
        raise EvaluationError("Indica un checkpoint .pt local existente")
    check_output_location(output, root, ignore_check)
    if output.exists():
        raise FileExistsError("La carpeta de salida ya existe; elige otra")
    if output == images_dir or output in images_dir.parents or images_dir in output.parents:
        raise EvaluationError("La salida y la carpeta de imágenes no pueden contenerse")
    manifest_data, items = load_reserved_images(manifest_path, images_dir, image_names)
    try:
        names = {int(key): str(value) for key, value in class_reader(checkpoint).items()}
    except (TypeError, ValueError) as exc:
        raise EvaluationError("No se pueden verificar las clases del checkpoint") from exc
    if names != EXPECTED_CLASSES:
        raise EvaluationError(f"El checkpoint debe tener solo la clase 0: nox_texto, no {names}")
    checkpoint_hash = file_hash(checkpoint)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".evaluation-", dir=output.parent) as temporary:
        staged = Path(temporary) / "run"
        (staged / "images").mkdir(parents=True)
        image_rows, detection_rows, review_images = [], [], []
        for index, item in enumerate(items, 1):
            entry = item["entry"]
            folder = f"{index:03d}_{item['path'].stem}"
            report = run_inference(
                item["path"], checkpoint, staged / "images" / folder, confidence=confidence,
                iou=iou, image_size=image_size, predictor=predictor,
            )
            if (report["image"]["width"], report["image"]["height"]) != (entry["width"], entry["height"]):
                raise EvaluationError(f"{entry['image']} no coincide con las dimensiones del manifiesto")
            if report["model"]["class_names"] != EXPECTED_CLASSES or report["model"]["sha256"] != checkpoint_hash:
                raise EvaluationError("El informe de inferencia no coincide con el checkpoint verificado")
            common = {"index": index, "image": entry["image"], "image_sha256": report["image"]["sha256"]}
            image_rows.append({
                **common, "width": report["image"]["width"], "height": report["image"]["height"],
                "annotated_boxes": len(entry.get("boxes") or []), "detection_count": report["detection_count"],
                "status": "detections" if report["detections"] else "no_detections",
                "predictions_json": f"images/{folder}/predictions.json",
                "annotated_png": f"images/{folder}/annotated.png",
            })
            for detection in report["detections"]:
                x1, y1, x2, y2 = detection["bbox_xyxy"]
                detection_rows.append({
                    **common, "checkpoint_sha256": checkpoint_hash, "detection_id": detection["detection_id"],
                    "class_id": detection["class_id"], "class_name": detection["class_name"],
                    "confidence": detection["confidence"], "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                })
            review_images.append({
                "image": entry["image"], "image_sha256": report["image"]["sha256"],
                "detections": [{"detection_id": d["detection_id"], "verdict": None} for d in report["detections"]],
                "missed_logos": None, "notes": "",
            })
        write_csv(staged / "summary.csv", [
            "index", "image", "image_sha256", "width", "height", "annotated_boxes", "detection_count",
            "status", "predictions_json", "annotated_png",
        ], image_rows)
        write_csv(staged / "detections.csv", [
            "index", "image", "image_sha256", "checkpoint_sha256", "detection_id", "class_id", "class_name",
            "confidence", "x1", "y1", "x2", "y2",
        ], detection_rows)
        run = {
            "schema_version": 1, "complete": True, "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "checkpoint": {"filename": checkpoint.name, "sha256": checkpoint_hash, "class_names": names},
            "manifest": {
                "filename": manifest_path.name, "sha256": file_hash(manifest_path), "status": manifest_data.get("status"),
                "independent_blind_test": manifest_data.get("independent_blind_test"),
                "rights_status": manifest_data.get("rights_status"), "limitations": manifest_data.get("limitations", []),
            },
            "partition": RESERVED_SPLIT,
            "parameters": {
                "confidence": confidence, "confidence_rationale": confidence_rationale, "iou": iou,
                "image_size": image_size, "device": "cpu",
            },
            "images": image_rows,
            "totals": {
                "images": len(image_rows), "detections": len(detection_rows),
                "images_with_detections": sum(row["detection_count"] > 0 for row in image_rows),
                "images_without_detections": sum(row["detection_count"] == 0 for row in image_rows),
            },
            "manual_review": "pending: fill review-template.json as review.json, then run the report command",
            "limitations": FIXED_LIMITATIONS,
        }
        (staged / "run.json").write_text(json.dumps(run, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
        template = {
            "schema_version": 1, "reviewed": False, "reviewer": None, "checkpoint_sha256": checkpoint_hash,
            "instructions": "Set reviewed=true and reviewer. Per detection: verdict is true_positive or false_positive. "
                            "Per image: missed_logos is the integer count of visible NOX text logos with no detection.",
            "images": review_images,
        }
        (staged / "review-template.json").write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        staged.rename(output)
    return run


def load_json(path, label):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise EvaluationError(f"No se puede leer {label}") from exc


def build_report(run_dir, review_path=None, *, root=ROOT, ignore_check=git_ignores):
    """Combine run outputs with the human review into counts and a Markdown report."""
    run_dir = Path(run_dir).resolve()
    check_output_location(run_dir, root, ignore_check)
    review_path = Path(review_path).resolve() if review_path else run_dir / "review.json"
    run, review = load_json(run_dir / "run.json", "run.json"), load_json(review_path, "la revisión manual")
    if run.get("complete") is not True:
        raise EvaluationError("La ejecución no está completa")
    if review.get("reviewed") is not True or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise EvaluationError("La revisión manual debe indicar reviewed=true y reviewer")
    if review.get("checkpoint_sha256") != run["checkpoint"]["sha256"]:
        raise EvaluationError("La revisión no corresponde al checkpoint de la ejecución")
    reviewed = {(item.get("image"), item.get("image_sha256")): item for item in review.get("images", [])}
    if len(reviewed) != len(review.get("images", [])) or set(reviewed) != {(row["image"], row["image_sha256"]) for row in run["images"]}:
        raise EvaluationError("La revisión no cubre exactamente las imágenes de la ejecución")
    images, false_positives, false_negatives, without = [], [], [], []
    counts = {"true_positives": 0, "false_positives": 0, "false_negatives": 0}
    for row in run["images"]:
        item = reviewed[(row["image"], row["image_sha256"])]
        predictions = load_json(run_dir / row["predictions_json"], row["predictions_json"])
        verdicts = {entry.get("detection_id"): entry.get("verdict") for entry in item.get("detections", [])}
        if sorted(verdicts) != [d["detection_id"] for d in predictions["detections"]] or len(verdicts) != len(item.get("detections", [])):
            raise EvaluationError(f"La revisión de {row['image']} no coincide con sus detecciones")
        if any(verdict not in VERDICTS for verdict in verdicts.values()):
            raise EvaluationError(f"Falta un veredicto válido en {row['image']}")
        missed = item.get("missed_logos")
        if isinstance(missed, bool) or not isinstance(missed, int) or missed < 0:
            raise EvaluationError(f"missed_logos de {row['image']} debe ser un entero no negativo")
        detections = []
        for detection in predictions["detections"]:
            verdict = verdicts[detection["detection_id"]]
            detections.append({
                "detection_id": detection["detection_id"], "class_name": detection["class_name"],
                "confidence": detection["confidence"], "bbox_xyxy": detection["bbox_xyxy"], "verdict": verdict,
            })
            counts["true_positives" if verdict == "true_positive" else "false_positives"] += 1
            if verdict == "false_positive":
                false_positives.append({"image": row["image"], **detections[-1]})
        counts["false_negatives"] += missed
        if missed:
            false_negatives.append({"image": row["image"], "missed_logos": missed})
        if not detections:
            without.append(row["image"])
        images.append({
            "image": row["image"], "image_sha256": row["image_sha256"], "detections": detections,
            "missed_logos": missed, "notes": str(item.get("notes", "")),
        })
    limitations = list(run["limitations"]) + [f"Manifest: {text}" for text in run["manifest"].get("limitations", [])]
    if run["manifest"].get("independent_blind_test") is not True:
        limitations.append("The reserved partition is not a blind independent test")
    report = {
        "schema_version": 1, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint": run["checkpoint"], "parameters": run["parameters"], "reviewer": review["reviewer"].strip(),
        "counts": {"images": len(images), "detections": counts["true_positives"] + counts["false_positives"], **counts,
                   "images_without_detections": len(without)},
        "images": images, "images_without_detections": without, "false_positives": false_positives,
        "false_negatives": false_negatives, "limitations": limitations,
    }
    markdown = render_markdown(report)
    json_path, markdown_path = run_dir / "report.json", run_dir / "report.md"
    if json_path.exists() or markdown_path.exists():
        raise FileExistsError("El informe ya existe; no se sobrescribe")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    return report


def cell(value):
    return str(value).replace("|", "/").replace("\n", " ")


def render_markdown(report):
    """Render counts and per-image findings without ratios or quality claims."""
    counts, parameters = report["counts"], report["parameters"]
    lines = [
        "# Evaluación única de nox_texto", "",
        f"- Checkpoint: `{report['checkpoint']['filename']}` (SHA-256 `{report['checkpoint']['sha256']}`)",
        f"- Umbral de confianza: {parameters['confidence']:g}. Motivo: {cell(parameters.get('confidence_rationale') or 'sin documentar')}",
        f"- Revisor: {cell(report['reviewer'])}", "",
        "## Recuentos revisados manualmente", "",
        "| Imágenes | Detecciones | Verdaderos positivos | Falsos positivos | Falsos negativos | Imágenes sin detecciones |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {counts['images']} | {counts['detections']} | {counts['true_positives']} | {counts['false_positives']} | "
        f"{counts['false_negatives']} | {counts['images_without_detections']} |", "",
        "## Detecciones por imagen", "",
        "| Imagen | ID | Score del modelo | Caja xyxy | Veredicto |", "| --- | --- | --- | --- | --- |",
    ]
    for image in report["images"]:
        for detection in image["detections"]:
            box = ", ".join(f"{value:.1f}" for value in detection["bbox_xyxy"])
            lines.append(f"| {cell(image['image'])} | {detection['detection_id']} | {detection['confidence']:.3f} | {box} | {detection['verdict']} |")
    lines += ["", "## Imágenes sin detecciones", ""] + ([f"- {cell(name)}" for name in report["images_without_detections"]] or ["Ninguna."])
    lines += ["", "## Falsos positivos", ""] + (
        [f"- {cell(item['image'])}, detección {item['detection_id']}" for item in report["false_positives"]] or ["Ninguno."])
    lines += ["", "## Falsos negativos", ""] + (
        [f"- {cell(item['image'])}: {item['missed_logos']} logo(s) sin detectar" for item in report["false_negatives"]] or ["Ninguno."])
    notes = [(image["image"], image["notes"]) for image in report["images"] if image["notes"].strip()]
    if notes:
        lines += ["", "## Notas del revisor", ""] + [f"- {cell(name)}: {cell(text)}" for name, text in notes]
    lines += ["", "## Límites", ""] + [f"- {cell(text)}" for text in report["limitations"]]
    return "\n".join(lines) + "\n"


def build_parser():
    parser = argparse.ArgumentParser(description="Evaluación única de un checkpoint nox_texto sobre imágenes reservadas")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="ejecutar la inferencia sobre la partición reservada")
    run.add_argument("--checkpoint", type=Path, required=True)
    run.add_argument("--images-dir", type=Path, required=True)
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--confidence", type=float, required=True)
    run.add_argument("--confidence-rationale")
    run.add_argument("--image", action="append", dest="image_names", help="nombre de una imagen reservada; repetible")
    run.add_argument("--iou", type=float, default=.7)
    run.add_argument("--image-size", type=int, default=640)
    report = commands.add_parser("report", help="generar el informe tras la revisión manual")
    report.add_argument("--run-dir", type=Path, required=True)
    report.add_argument("--review", type=Path)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run_evaluation(
                checkpoint=args.checkpoint, images_dir=args.images_dir, manifest=args.manifest, output=args.output,
                confidence=args.confidence, image_names=args.image_names, confidence_rationale=args.confidence_rationale,
                iou=args.iou, image_size=args.image_size,
            )
            print(json.dumps({"complete": True, **result["totals"], "output": str(args.output.resolve())}, ensure_ascii=False))
        else:
            result = build_report(args.run_dir, args.review)
            print(json.dumps({"complete": True, **result["counts"], "output": str(args.run_dir.resolve())}, ensure_ascii=False))
    except (PredictionError, OSError, RuntimeError) as exc:
        parser.exit(2, f"Error de evaluación: {exc}\n")


if __name__ == "__main__":
    main()
