"""Combine reviewed NOX wordmarks into a separate, traceable local dataset."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image, ImageDraw


def digest(path):
    """Hash a file without retaining all bytes."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build(root, previous):
    """Preserve old splits and lock each new source group to one partition."""
    root, previous = root.resolve(), previous.resolve()
    output = root / "data/review/nox-text-dataset-2026-11-03"
    archive_path = output.with_suffix(".zip")
    if output.exists() or archive_path.exists():
        raise FileExistsError("Refusing to overwrite a dataset or archive")
    old = json.loads((previous / "manifest.json").read_text(encoding="utf-8"))
    review_path = root / "docs/nox-text-review-2026-11-03.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    candidates = json.loads((root / "docs/nox-new-source-candidates-2026-10-30.json").read_text(encoding="utf-8"))
    groups = {item["video_id"]: item["provisional_group_id"] for item in candidates["sources"]}
    assignments = {"milano-p1": "train", "germany-p2": "val", "kuwait-2026-provisional": "train", "kuwait-2025-provisional": "test"}
    records = []
    for item in old["images"]:
        source = previous / item["image"]
        assert digest(source) == item["source_sha256"]
        assert digest(previous / item["label"]) == item["label_sha256"]
        assert assignments[item["group_id"]] == item["split"]
        records.append(dict(source=source, source_sha256=item["source_sha256"], video_id=item["video_id"], group_id=item["group_id"], split=item["split"], boxes=item["boxes_xyxy"], annotation_source=item["annotation_source"], original_class="nox", review="Previous 13 target crops rechecked as text; original full-image reviews retained"))
    for item in review["images"]:
        if item["decision"] == "excluded":
            continue
        source = root / item["source_image"]
        assert digest(source) == item["image_sha256"]
        group = groups[item["video_id"]]
        records.append(dict(source=source, source_sha256=item["image_sha256"], video_id=item["video_id"], group_id=group, split=assignments[group], boxes=[b["bbox_xyxy"] for b in item["boxes"]], annotation_source=review_path.name + ":" + item["id"], original_class="nox_texto", review=item["reason"]))
    assert len({r["source_sha256"] for r in records}) == len(records)
    for record in records:
        with Image.open(record["source"]) as image:
            image.load()
            record["width"], record["height"] = image.size
        for x1, y1, x2, y2 in record["boxes"]:
            assert 0 <= x1 < x2 <= record["width"] and 0 <= y1 < y2 <= record["height"]
    summary = {}
    for split in ("train", "val", "test"):
        subset = [r for r in records if r["split"] == split]
        summary[split] = dict(images=len(subset), positives=sum(bool(r["boxes"]) for r in subset), negatives=sum(not r["boxes"] for r in subset), boxes=sum(len(r["boxes"]) for r in subset))
        for other in ("train", "val", "test"):
            if other != split:
                assert not {r["group_id"] for r in subset} & {r["group_id"] for r in records if r["split"] == other}
    output.mkdir(parents=True)
    for record in records:
        split = record["split"]
        name = record["video_id"] + "_" + record["source_sha256"][:12]
        image_path = output / "images" / split / (name + ".png")
        label_path = output / "labels" / split / (name + ".txt")
        image_path.parent.mkdir(parents=True, exist_ok=True)
        label_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(record["source"], image_path)
        assert digest(image_path) == record["source_sha256"]
        rows = []
        for x1, y1, x2, y2 in record["boxes"]:
            w, h = record["width"], record["height"]
            values = [(x1+x2)/(2*w), (y1+y2)/(2*h), (x2-x1)/w, (y2-y1)/h]
            row = "0 " + " ".join(f"{v:.10f}" for v in values)
            cx, cy, bw, bh = map(float, row.split()[1:])
            restored = [(cx-bw/2)*w, (cy-bh/2)*h, (cx+bw/2)*w, (cy+bh/2)*h]
            assert max(abs(a-b) for a,b in zip(restored,(x1,y1,x2,y2))) < .001
            rows.append(row)
        label_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
        record["source"] = str(record["source"])
        record["image"], record["label"] = image_path.relative_to(output).as_posix(), label_path.relative_to(output).as_posix()
        record["label_sha256"] = digest(label_path)
        with Image.open(image_path) as image:
            preview = image.convert("RGB")
            draw = ImageDraw.Draw(preview)
            for box in record["boxes"]:
                draw.rectangle(tuple(box), outline="#00ff00", width=2)
            target = output / "previews" / split / (name + ".jpg")
            target.parent.mkdir(parents=True, exist_ok=True)
            preview.save(target, quality=94)
    yaml_tail = "\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: nox_texto\n"
    (output / "dataset.yaml").write_text("path: " + json.dumps(output.as_posix()) + yaml_tail, encoding="utf-8")
    manifest = {"date":"2026-11-03", "status":"exploratory_text_only_dataset_human_acceptance_pending", "classes":{"0":"nox_texto"}, "summary":summary, "group_assignment":assignments, "review_sha256":digest(review_path), "previous_manifest_sha256":digest(previous / "manifest.json"), "coordinate_round_trip_tolerance_pixels":.001, "independent_blind_test":False, "rights_status":"Reuse permissions remain pending; no external upload or training in this block", "limitations":["Test has one inspected image, not a sufficient independent final evaluation", "Group identity is provisional; no verified match-level independence", "Wordmark-only priority approved by user; independent symbol not learned"], "images":records}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    with ZipFile(archive_path, "x", ZIP_DEFLATED) as archive:
        for record in records:
            for field in ("image", "label"):
                path = output / record[field]
                archive.write(path, "nox-text-2026-11-03/" + record[field])
        archive.writestr("nox-text-2026-11-03/dataset.yaml", "path: /content/nox-text-2026-11-03" + yaml_tail)
        archive.write(output / "manifest.json", "nox-text-2026-11-03/manifest.json")
    with ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == 2*len(records)+2
    public = dict(manifest)
    public["images"] = [{k:v for k,v in r.items() if k != "source"} for r in records]
    public["archive_sha256"] = digest(archive_path)
    (root / "docs/nox-text-dataset-2026-11-03.json").write_text(json.dumps(public, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--previous-dataset", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root, args.previous_dataset)))
