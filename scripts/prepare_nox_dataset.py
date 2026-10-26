"""Build a local YOLO-format pilot dataset using reviewed source-group locks."""

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

from PIL import Image


SPLITS = {"milano-p1": "train", "germany-p2": "val"}
INVENTORY = "docs/nox-review-inventory-2026-10-26.json"
GROUPS = "docs/nox-source-groups-2026-10-26.json"
PILOT = "data/review/exports/nox-cvat-export-2026-10-23/verification.json"
EXPANSION = "docs/nox-expansion-review-2026-10-23.json"
EXPANSION_MANIFEST = "data/review/nox-expansion-2026-10-23/manifest.json"
USER_REVIEWS = (
    "docs/review-user-moments-decisions-2026-10-26.json",
    "docs/review-user-video2-decisions-2026-10-26.json",
)


def digest(path):
    """Identify the exact bytes of an input or generated file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalized_box(box, width, height):
    """Convert valid original-pixel xyxy coordinates to YOLO xywh."""
    if len(box) != 4 or any(type(value) not in (int, float) or not math.isfinite(value) for value in box):
        raise ValueError("Expected four finite numeric box coordinates")
    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions")
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        raise ValueError("Box outside image or with zero area")
    return [(x1 + x2) / (2 * width), (y1 + y2) / (2 * height), (x2 - x1) / width, (y2 - y1) / height]


def annotation_sources(root):
    """Prefer saved CVAT coordinates, then the first reviewed annotation."""
    result = {}
    for item in read_json(root / PILOT)["examples"]:
        result[item["image_sha256"]] = {
            "source": PILOT + ":" + item["id"],
            "boxes": [{"label": "nox", "bbox_xyxy": box["bbox_xyxy"], **box["attributes"]} for box in item["boxes"]],
        }
    originals = {item["id"]: item for item in read_json(root / EXPANSION_MANIFEST)["examples"]}
    for item in read_json(root / EXPANSION)["examples"]:
        result.setdefault(originals[item["id"]]["image_sha256"], {"source": EXPANSION + ":" + item["id"], "boxes": item["boxes"]})
    for filename in USER_REVIEWS:
        for item in read_json(root / filename)["examples"]:
            result.setdefault(item["image_sha256"], {"source": filename + ":" + str(item["reference_seconds"]), "boxes": item["boxes"]})
    return result


def build_dataset(project_root, output):
    """Validate every selected input before writing an immutable local package."""
    root = project_root.resolve()
    output = output.resolve()
    allowed = (root / "data/review").resolve()
    if not output.is_relative_to(allowed) or output == allowed:
        raise ValueError("Output must be a subdirectory of ignored data/review")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite: {output}")
    inventory = read_json(root / INVENTORY)
    grouping = read_json(root / GROUPS)
    if grouping["inventory_sha256"] != digest(root / INVENTORY):
        raise ValueError("Grouping refers to a stale inventory")
    groups = {item["image_sha256"]: item for item in grouping["images"]}
    inventory_hashes = [item["image_sha256"] for item in inventory["images"]]
    if len(set(inventory_hashes)) != len(inventory_hashes) or len(groups) != len(grouping["images"]):
        raise ValueError("Duplicate image hash in inventory or grouping")
    if set(groups) != set(inventory_hashes):
        raise ValueError("Grouping and inventory coverage differ")
    annotations = annotation_sources(root)
    selected, excluded = [], []
    for item in inventory["images"]:
        image_hash = item["image_sha256"]
        group = groups[image_hash]
        if group["video_id"] != item["video_id"] or group["review_status"] != item["review_status"]:
            raise ValueError("Grouping and inventory disagree")
        status = item["review_status"]
        if status not in {"positive_without_recorded_ambiguity", "reviewed_negative"}:
            excluded.append({"image_sha256": image_hash, "review_status": status})
            continue
        if item["ambiguous_region"]:
            raise ValueError("Selected image still contains an ambiguous region")
        source = (root / item["source_image"]).resolve()
        if not source.is_relative_to(allowed) or digest(source) != image_hash:
            raise ValueError("Source image path or hash mismatch")
        annotation = annotations[image_hash]
        boxes = annotation["boxes"]
        positive = status == "positive_without_recorded_ambiguity"
        if positive != bool(boxes) or len(boxes) != item["clear_box_count"]:
            raise ValueError("Annotation count disagrees with review status")
        with Image.open(source) as image:
            image.load()
            width, height = image.size
            if image.format != "PNG":
                raise ValueError("Expected original PNG")
        rows = []
        for box in boxes:
            if box["label"] != "nox" or box.get("visibility") != "clear":
                raise ValueError("Only clear NOX annotations can be exported")
            values = normalized_box(box["bbox_xyxy"], width, height)
            rows.append("0 " + " ".join(f"{value:.10f}" for value in values))
        group_id = group["group_id"]
        if group_id not in SPLITS:
            raise ValueError("Unknown source group")
        selected.append({
            "source_image": source.relative_to(root).as_posix(), "source_sha256": image_hash,
            "video_id": item["video_id"], "group_id": group_id, "split": SPLITS[group_id],
            "width": width, "height": height, "positive": positive,
            "annotation_source": annotation["source"], "boxes_xyxy": [box["bbox_xyxy"] for box in boxes],
            "label_text": "\n".join(rows) + ("\n" if rows else ""),
            "name": item["video_id"] + "_" + image_hash[:12],
        })
    if {item["split"] for item in selected} != {"train", "val"}:
        raise ValueError("Both exploratory splits must be nonempty")
    for key in ("source_sha256", "video_id", "group_id"):
        train = {item[key] for item in selected if item["split"] == "train"}
        validation = {item[key] for item in selected if item["split"] == "val"}
        if train & validation:
            raise ValueError(f"Cross-split overlap: {key}")
    if len({item["name"] for item in selected}) != len(selected):
        raise ValueError("Destination name collision")
    output.mkdir(parents=True)
    for split in ("train", "val"):
        (output / "images" / split).mkdir(parents=True)
        (output / "labels" / split).mkdir(parents=True)
    for item in selected:
        image_path = output / "images" / item["split"] / (item["name"] + ".png")
        label_path = output / "labels" / item["split"] / (item["name"] + ".txt")
        shutil.copyfile(root / item["source_image"], image_path)
        if digest(image_path) != item["source_sha256"]:
            raise ValueError("Copied image hash mismatch")
        label_path.write_text(item.pop("label_text"), encoding="utf-8")
        label_rows = label_path.read_text(encoding="utf-8").splitlines()
        if len(label_rows) != len(item["boxes_xyxy"]):
            raise ValueError("Serialized annotation count mismatch")
        for row, original_box in zip(label_rows, item["boxes_xyxy"]):
            class_id, *values = row.split()
            if class_id != "0" or len(values) != 4:
                raise ValueError("Invalid YOLO label row")
            cx, cy, bw, bh = map(float, values)
            restored = [(cx-bw/2)*item["width"], (cy-bh/2)*item["height"], (cx+bw/2)*item["width"], (cy+bh/2)*item["height"]]
            if max(abs(a-b) for a, b in zip(original_box, restored)) > 0.001:
                raise ValueError("Label round-trip exceeds 0.001 pixel")
        item["image"] = image_path.relative_to(output).as_posix()
        item["label"] = label_path.relative_to(output).as_posix()
        item["label_sha256"] = digest(label_path)
        del item["name"]
    source_files = (INVENTORY, GROUPS, PILOT, EXPANSION, EXPANSION_MANIFEST, *USER_REVIEWS)
    summary = {split: {"images": sum(item["split"] == split for item in selected), "positive_images": sum(item["split"] == split and item["positive"] for item in selected), "negative_images": sum(item["split"] == split and not item["positive"] for item in selected), "boxes": sum(len(item["boxes_xyxy"]) for item in selected if item["split"] == split)} for split in ("train", "val")}
    manifest = {
        "schema_version": 1, "status": "local_exploratory_dataset_not_final_evaluation",
        "class_names": {"0": "nox"}, "group_assignment": SPLITS, "summary": summary,
        "source_files_sha256": {name: digest(root / name) for name in source_files},
        "annotation_precedence": "Saved CVAT export, then original expansion review, then user timestamp reviews. Repeated frames are exported once.",
        "test_split": None, "training_executed": False, "ultralytics_loader_tested": False,
        "rights_status": "Pending documented permission and distribution review before external upload or training.",
        "limits": ["Tiny exploratory dataset; validation has only one positive in the current material.", "Conservative metadata-based event grouping does not prove match identity.", "No independent test set; validation cannot be presented as final evaluation.", "Positive images are concentrated in similar shots, and validation changes support from shirts to a wristband."],
        "excluded_images": excluded, "images": selected,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    yaml = "# Local exploratory NOX dataset; regenerate path if relocating.\npath: " + json.dumps(output.as_posix()) + "\ntrain: images/train\nval: images/val\nnames:\n  0: nox\n"
    (output / "dataset.yaml").write_text(yaml, encoding="utf-8")
    verification = {"image_hashes_verified": len(selected), "labels_verified": len(selected), "box_round_trip_tolerance_pixels": 0.001, "group_video_and_image_overlap": 0, "summary": summary, "excluded_image_count": len(excluded), "test_split_created": False, "training_executed": False}
    (output / "verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("data/review/nox-exploratory-dataset-2026-10-26"))
    args = parser.parse_args()
    result = build_dataset(args.project_root, args.project_root / args.output)
    print(json.dumps({"summary": result["summary"], "excluded": len(result["excluded_images"]), "training_executed": False}))


if __name__ == "__main__":
    main()
