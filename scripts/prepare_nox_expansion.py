"""Package existing source frames as unlabelled candidates for manual review."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from PIL import Image


repo = Path(__file__).resolve().parents[1]
destination = repo / "data/review/nox-expansion-2026-10-23"
selections = [
    ("player-moments-2026-10-21", "7695444675531951382", "T01", "Side/back clothing candidate"),
    ("player-moments-2026-10-21", "7695444675531951382", "T02", "Different brand clothing; inspect full image for NOX"),
    ("player-moments-2026-10-21", "7695453226648292630", "T02", "Partially occluded chest candidate"),
    ("player-moments-2026-10-21", "7695453226648292630", "T05", "Lower-back candidate near image boundary"),
    ("player-moments-2026-10-21", "7695453226648292630", "T09", "Side view; inspect clothing and paddle"),
    ("player-moments-2026-10-21", "7697671396830317846", "T01", "Action view with small clothing and paddle regions"),
    ("player-moments-2026-10-21", "7697671396830317846", "T02", "Other-brand back view; inspect all supports"),
    ("targeted-2026-10-21", "7697683756945280279", "T01", "Front NOX clothing candidate"),
    ("targeted-2026-10-21", "7697683756945280279", "T05", "Other-brand clothing; candidate negative only after full review"),
    ("targeted-2026-10-21", "7697683756945280279", "T07", "Action view and paddle candidate"),
    ("targeted-2026-10-21", "7698076371569888534", "T03", "Occluded clothing candidate"),
    ("targeted-2026-10-21", "7698076371569888534", "T09", "Wider view with occlusion; inspect every logo"),
]
records = []
hashes = set()
for number, (run, video_id, sample_id, reason) in enumerate(selections, 1):
    source_root = repo / "data/review" / run
    manifest = json.loads((source_root / "manifest.json").read_text(encoding="utf-8"))
    video = next(item for item in manifest["videos"] if item["video_id"] == video_id)
    sample = next(item for item in video["samples"] if item["sample_id"] == sample_id)
    source = source_root / sample["image"]
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest not in hashes
    hashes.add(digest)
    with Image.open(source) as image:
        dimensions = list(image.size)
    records.append({
        "id": f"E{number:02d}",
        "source_image": source.relative_to(repo).as_posix(),
        "source_manifest": (source_root / "manifest.json").relative_to(repo).as_posix(),
        "image": f"images/E{number:02d}_{video_id}_f{sample['frame_index']:06d}.png",
        "image_sha256": digest,
        "video_id": video_id,
        "video_sha256": video["sha256"],
        "source_url": video["source_url"],
        "frame_index": sample["frame_index"],
        "reference_seconds": sample["reference_seconds"],
        "dimensions": dimensions,
        "selection_reason": reason,
        "annotation_status": "unreviewed_candidate",
        "evidence_category": None,
        "negative_status": "not_approved",
        "split": None,
        "cross_video_origin_group": "pending_scene_review",
    })
destination.mkdir(parents=True, exist_ok=False)
(destination / "images").mkdir()
for record in records:
    output = destination / record["image"]
    shutil.copyfile(repo / record["source_image"], output)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == record["image_sha256"]
with zipfile.ZipFile(destination / "images.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for record in records:
        archive.write(destination / record["image"], arcname=Path(record["image"]).name)
with zipfile.ZipFile(destination / "images.zip") as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(records)
    for record in records:
        assert hashlib.sha256(archive.read(Path(record["image"]).name)).hexdigest() == record["image_sha256"]
output_manifest = {
    "date_local": "2026-10-23",
    "status": "unlabelled_review_candidates_not_training_dataset",
    "image_count": len(records),
    "video_count": len({record["video_id"] for record in records}),
    "rights_status": "not_resolved_by_packaging; confirm existing material conditions before further cloud upload or training",
    "images_zip_sha256": hashlib.sha256((destination / "images.zip").read_bytes()).hexdigest(),
    "selection_limits": "Selection from existing contact sheets is biased, not representative. No labels or negatives approved. Different videos may reuse scenes or belong to the same match. No random frame split.",
    "examples": records,
}
(destination / "manifest.json").write_text(json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
lines = ["# Lote de ampliación NOX — 23/10/2026", "", "12 candidatos locales de cinco vídeos; imágenes originales conservadas byte por byte. No son positivos ni negativos aprobados y no tienen partición asignada. No se ha subido este lote a CVAT ni se ha entrenado.", "", "Revisar cada imagen completa, localizar todas las apariciones de NOX y diferenciar ropa/pala/estático. No convertir regiones ambiguas en fondo de entrenamiento. Mantener escenas relacionadas juntas al particionar y revisar permisos antes de usar nuevos servicios.", "", "| ID | Vídeo | Segundo | Motivo de selección | Original |", "| --- | --- | --- | --- | --- |"]
for record in records:
    lines.append(f"| {record['id']} | {record['video_id']} | {record['reference_seconds']} | {record['selection_reason']} | [PNG]({record['image']}) |")
(destination / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"destination": str(destination), "images": len(records), "videos": output_manifest["video_count"], "zip_integrity_and_image_hashes": "passed"}))
