"""Preserve and check the reviewed pilot without altering source annotations."""

import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


repo = Path(__file__).resolve().parents[1]
workspace = repo / "data/review"
archive_path = Path.home() / "Downloads/nox-pilot-cvat-2026-10-23.zip"
batch = repo / "data/review/nox-cvat-pilot-2026-10-21"
manifest = json.loads((batch / "manifest.json").read_text(encoding="utf-8"))
expected = {Path(item["image"]).name: item for item in manifest["examples"]}
previous = json.loads((batch / "exports/2026-10-22-job-4626112/verification.json").read_text(encoding="utf-8"))
previous_by_id = {item["id"]: item for item in previous["examples"]}
expected_attributes = {
    "N01": [("clear", "clothing")],
    "N02": [("pending", "paddle"), ("clear", "clothing")],
    "N03": [("possible", "clothing")],
}
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    assert archive.namelist() == ["annotations.xml"]
    xml = archive.read("annotations.xml")
root = ET.fromstring(xml)
assert root.tag == "annotations" and root.findtext("version") == "1.1"
records = []
seen = set()
for node in root.findall("image"):
    name = node.get("name")
    assert name in expected and name not in seen
    seen.add(name)
    source = expected[name]
    image_path = batch / source["image"]
    assert sha256(image_path) == source["image_sha256"]
    with Image.open(image_path) as original:
        width, height = original.size
    assert (width, height) == (int(node.get("width")), int(node.get("height")))
    boxes = []
    for box in node.findall("box"):
        coords = [float(box.get(key)) for key in ("xtl", "ytl", "xbr", "ybr")]
        assert all(math.isfinite(value) for value in coords)
        x1, y1, x2, y2 = coords
        assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
        assert box.get("label") == "nox"
        attrs = {attr.get("name"): attr.text for attr in box.findall("attribute")}
        boxes.append({"bbox_xyxy": coords, "attributes": attrs})
    assert [(box["attributes"]["visibility"], box["attributes"]["support"]) for box in boxes] == expected_attributes[source["id"]]
    assert [box["bbox_xyxy"] for box in boxes] == [box["bbox_xyxy"] for box in previous_by_id[source["id"]]["boxes"]]
    records.append({"id": source["id"], "image": name, "image_sha256": source["image_sha256"], "boxes": boxes})
assert seen == set(expected)
destination = workspace / "exports/nox-cvat-export-2026-10-23"
destination.mkdir(parents=True, exist_ok=False)
shutil.copyfile(archive_path, destination / archive_path.name)
(destination / "annotations.xml").write_bytes(xml)
report = {
    "date_local": "2026-10-23",
    "job_url": "https://app.cvat.ai/tasks/2694276/jobs/4626112",
    "archive_sha256": sha256(archive_path),
    "xml_sha256": hashlib.sha256(xml).hexdigest(),
    "structural_validation": "passed",
    "expected_attributes_verified": True,
    "coordinates_unchanged_from_previous_export": True,
    "image_count": len(records),
    "box_count": sum(len(item["boxes"]) for item in records),
    "native_originals_visually_inspected": True,
    "semantic_limits": "Paddle region pending; N03 possible. N02 is not ready for ordinary training with all boxes treated as positives. No training splits or labels created.",
    "examples": records,
}
(destination / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"destination": str(destination), "image_count": report["image_count"], "box_count": report["box_count"], "validation": "passed"}))
