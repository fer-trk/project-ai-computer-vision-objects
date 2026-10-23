"""Package original review images for manual annotation in CVAT."""

import argparse
import hashlib
import json
import math
import re
import shutil
import zipfile
from pathlib import Path

from PIL import Image


def file_hash(path):
    """Hash files incrementally, including large source videos."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inside(root, value):
    """Resolve paths without allowing references outside the given root."""
    root = root.resolve()
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path leaves the allowed directory: {value}")
    return path


def read_json(path):
    """Accept JSON files saved with or without a UTF-8 BOM."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_examples(root, pilot_path):
    """Check image integrity, proposed boxes and exact extraction provenance."""
    pilot = read_json(pilot_path)
    if pilot.get("first_brand") != "NOX" or pilot.get("schema_version") != 1:
        raise ValueError("Expected the version 1 NOX review pilot.")
    examples = pilot.get("examples", [])
    if not examples:
        raise ValueError("The pilot has no examples.")
    records = []
    seen_ids, seen_hashes, seen_frames = set(), set(), set()
    video_hashes = {}
    for item in examples:
        identifier = item["id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+", identifier) or identifier in seen_ids:
            raise ValueError(f"Invalid or duplicate example ID: {identifier}")
        source = inside(root / "data/review", inside(root, item["image"]))
        if not source.is_file():
            raise ValueError(f"Missing source image: {item['image']}")
        image_hash = file_hash(source)
        if image_hash != item["image_sha256"]:
            raise ValueError(f"Image hash mismatch: {identifier}")
        frame_key = (item["video_id"], item["frame_index"])
        if image_hash in seen_hashes or frame_key in seen_frames:
            raise ValueError(f"Duplicate image or source frame: {identifier}")
        if item.get("brand") != "NOX":
            raise ValueError(f"Unexpected brand: {identifier}")
        with Image.open(source) as image:
            image.load()
            width, height = image.size
            if image.format != "PNG":
                raise ValueError(f"Expected an original PNG: {identifier}")
        if [width, height] != [item["image_width"], item["image_height"]]:
            raise ValueError(f"Image dimensions mismatch: {identifier}")
        box = item.get("proposed_bbox_xyxy")
        if box is not None:
            if len(box) != 4 or any(type(value) is not int for value in box):
                raise ValueError(f"Expected four integer box coordinates: {identifier}")
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
                raise ValueError(f"Proposed box outside image: {identifier}")
        manifest_path = inside(root / "data/review", source.parents[2] / "manifest.json")
        source_manifest = read_json(manifest_path)
        matches = []
        for video in source_manifest["videos"]:
            if video["video_id"] != item["video_id"]:
                continue
            for sample in video["samples"]:
                if inside(manifest_path.parent, sample["image"]) == source:
                    matches.append((video, sample))
        if len(matches) != 1:
            raise ValueError(f"Expected one extraction manifest entry: {identifier}")
        video, sample = matches[0]
        timestamp = item["timestamp_seconds"]
        if (
            sample["frame_index"] != item["frame_index"]
            or not math.isfinite(timestamp)
            or not math.isclose(timestamp, sample["reference_seconds"], abs_tol=1e-6, rel_tol=0)
            or [sample["width"], sample["height"]] != [width, height]
        ):
            raise ValueError(f"Extraction reference mismatch: {identifier}")
        video_path = inside(root / "data/raw/videos", video["filename"])
        if video_path not in video_hashes:
            video_hashes[video_path] = file_hash(video_path)
        if video_hashes[video_path] != video["sha256"]:
            raise ValueError(f"Source video hash mismatch: {identifier}")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", item["video_id"]):
            raise ValueError(f"Unsafe video ID: {identifier}")
        if type(item["frame_index"]) is not int or item["frame_index"] < 0:
            raise ValueError(f"Invalid frame index: {identifier}")
        name = f"{identifier}_{item['video_id']}_f{item['frame_index']:06d}.png"
        records.append({
            "id": identifier,
            "image": "images/" + name,
            "image_sha256": image_hash,
            "width": width,
            "height": height,
            "source_image": source.relative_to(root).as_posix(),
            "source_manifest": manifest_path.relative_to(root).as_posix(),
            "video_id": item["video_id"],
            "video_sha256": video["sha256"],
            "source_url": video["source_url"],
            "frame_index": item["frame_index"],
            "timestamp_seconds": timestamp,
            "timestamp_basis": sample["timestamp_basis"],
            "label": "nox",
            "support": item["support"],
            "placement": item["placement"],
            "original_evidence_category": item["evidence_category"],
            "proposed_evidence_category": item.get("proposed_evidence_category"),
            "proposed_bbox_xyxy": box,
            "bbox_status": item["bbox_status"],
            "annotation_status": "pending_manual_review",
            "split": None,
            "origin_group_hint": item["video_id"],
            "cross_video_scene_group_status": "pending_review",
        })
        seen_ids.add(identifier)
        seen_hashes.add(image_hash)
        seen_frames.add(frame_key)
    return records


def prepare_batch(root, pilot_path, output, check_only=False):
    """Validate before writing and never convert proposals to training labels."""
    root = root.resolve()
    pilot_path = inside(root, pilot_path)
    output = inside(root / "data/review", inside(root, output))
    if output == (root / "data/review").resolve():
        raise ValueError("Choose a batch subdirectory under data/review.")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing batch: {output}")
    records = validate_examples(root, pilot_path)
    if check_only:
        return records
    (output / "images").mkdir(parents=True)
    with zipfile.ZipFile(output / "images.zip", mode="x", compression=zipfile.ZIP_STORED) as archive:
        for record in records:
            destination = output / record["image"]
            shutil.copyfile(root / record["source_image"], destination)
            if file_hash(destination) != record["image_sha256"]:
                raise ValueError(f"Copied image hash mismatch: {record['id']}")
            archive.write(destination, arcname=destination.name)
    manifest = {
        "schema_version": 1,
        "status": "unannotated_review_batch_not_training_dataset",
        "pilot": pilot_path.relative_to(root).as_posix(),
        "pilot_sha256": file_hash(pilot_path),
        "script_sha256": file_hash(Path(__file__)),
        "label": "nox",
        "image_count": len(records),
        "origin_grouping": "Video IDs are hints; review shared scenes across different videos before splitting.",
        "rights_status": "pending_review_before_cloud_upload_or_distribution",
        "images_zip_sha256": file_hash(output / "images.zip"),
        "examples": records,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = [
        "# Lote piloto NOX para CVAT", "",
        f"{len(records)} ejemplos de revisión; no es un dataset de entrenamiento.", "",
        "Subir images.zip después de revisar el uso del material. Contiene solo imágenes originales, sin cajas ni etiquetas.", "",
        "Anotar con la clase nox y atributos visibility/support. Conservar exportación CVAT con atributos además de YOLO.", "",
        "| ID | Imagen completa | Segundo | Claridad previa | Caja |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in records:
        category = record["original_evidence_category"] or "pendiente"
        index.append(f"| {record['id']} | [{Path(record['image']).name}]({record['image']}) | {record['timestamp_seconds']:g} | {category} | pendiente de revisión |")
    (output / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pilot", type=Path, default=Path("docs/nox-pilot.json"))
    parser.add_argument("--output", type=Path, default=Path("data/review/nox-cvat-pilot-2026-10-21"))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    output = args.project_root / args.output
    try:
        records = prepare_batch(args.project_root, args.pilot, output, args.check_only)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f"Error: {error}\n")
    verb = "Validated" if args.check_only else "Prepared"
    print(f"{verb} {len(records)} original images; 0 approved boxes exported; no training split created.")
    if not args.check_only:
        print(f"CVAT image archive: {output / 'images.zip'}")


if __name__ == "__main__":
    main()
