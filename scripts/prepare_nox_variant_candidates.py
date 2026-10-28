"""Select local variant-review candidates without publishing or labeling media."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
from PIL import Image


def digest(path):
    """Hash source bytes in bounded memory."""
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fingerprint(image):
    """Describe coarse visual similarity, not logo identity or scene independence."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype("float32")
    values = cv2.dct(gray)[:8, :8].flatten()[1:]
    threshold = sorted(values)[len(values) // 2]
    return sum(int(value > threshold) << index for index, value in enumerate(values))


def select_candidates(pool, references, per_video=10, minimum_distance=8, minimum_seconds=1.5):
    """Choose visually separated candidates in balanced rounds over source videos."""
    selected = []
    remaining = list(pool)
    videos = sorted({item["video_id"] for item in pool})
    for _ in range(per_video):
        for video in videos:
            available = [item for item in remaining if item["video_id"] == video and all(abs(item["seconds"] - other["seconds"]) >= minimum_seconds for other in selected if other["video_id"] == video)]
            if not available:
                continue
            anchors = references + [item["fingerprint"] for item in selected]
            distance = lambda item: min(((item["fingerprint"] ^ anchor).bit_count() for anchor in anchors), default=63)
            best = max(available, key=lambda item: (distance(item), -item["frame_index"]))
            if distance(best) <= minimum_distance:
                continue
            best = dict(best, minimum_distance_when_selected=distance(best))
            selected.append(best)
            remaining = [item for item in remaining if (item["video_id"], item["frame_index"]) != (best["video_id"], best["frame_index"])]
    return selected


def prepare(root):
    """Scan videos progressively and preserve only the selected original frames."""
    root = root.resolve()
    output = root / "data/review/nox-variant-candidates-2026-10-28"
    if output.exists():
        raise FileExistsError("Refusing to overwrite existing review candidates")
    inventory_path = root / "docs/nox-review-inventory-2026-10-26.json"
    groups_path = root / "docs/nox-source-groups-2026-10-26.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
    groups = json.loads(groups_path.read_text(encoding="utf-8-sig"))
    assert groups["inventory_sha256"] == digest(inventory_path)
    references = []
    reviewed_hashes = {item["image_sha256"] for item in inventory["images"]}
    for item in inventory["images"]:
        path = root / item["source_image"]
        assert digest(path) == item["image_sha256"]
        references.append(fingerprint(cv2.imread(str(path))))
    videos, pool = {}, []
    for video_id, group in sorted(groups["videos"].items()):
        path = root / "data/raw/videos" / (video_id + ".mp4")
        assert digest(root / group["metadata_path"]) == group["metadata_sha256"]
        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise ValueError(f"Cannot open video {video_id}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        assert math.isfinite(fps) and fps > 0 and frame_count > 0
        targets = {int((second + 0.5) * fps) for second in range(math.ceil(frame_count / fps))}
        index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if index in targets:
                    pool.append({"video_id": video_id, "frame_index": index, "seconds": index / fps, "fingerprint": fingerprint(frame)})
                index += 1
        finally:
            capture.release()
        assert index == frame_count
        videos[video_id] = {"source_video": path.relative_to(root).as_posix(), "video_sha256": digest(path), "group_id": group["group_id"], "frames": frame_count, "fps": fps, "source_url": group["source_url"]}
    selected = select_candidates(pool, references)
    if not selected:
        raise ValueError("No visually separated candidates found")
    output.mkdir(parents=True)
    saved = []
    image_hashes = set()
    for video_id, video in videos.items():
        wanted = {item["frame_index"]: item for item in selected if item["video_id"] == video_id}
        if not wanted:
            continue
        capture = cv2.VideoCapture(str(root / video["source_video"]))
        index = 0
        try:
            while wanted:
                ok, frame = capture.read()
                if not ok:
                    raise ValueError("Selected frame could not be decoded again")
                if index in wanted:
                    item = wanted.pop(index)
                    assert fingerprint(frame) == item["fingerprint"]
                    relative = f"images/{video_id}_f{index:06d}.png"
                    path = output / relative
                    path.parent.mkdir(exist_ok=True)
                    Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(path)
                    image_hash = digest(path)
                    assert image_hash not in reviewed_hashes | image_hashes
                    image_hashes.add(image_hash)
                    saved.append({"video_id": video_id, "video_sha256": video["video_sha256"], "group_id": video["group_id"], "frame_index": index, "reference_seconds": round(item["seconds"], 6), "timestamp_basis": "frame_index_over_reported_fps_estimate", "width": frame.shape[1], "height": frame.shape[0], "source_image": (output / relative).relative_to(root).as_posix(), "image_sha256": image_hash, "fingerprint_hex": f"{item['fingerprint']:016x}", "minimum_distance_when_selected": item["minimum_distance_when_selected"], "review_status": "pending_visual_review", "boxes": None, "variant": None, "split": None})
                index += 1
        finally:
            capture.release()
    assert len(saved) == len(selected)
    result = {"schema_version": 1, "date_local": "2026-10-28", "status": "candidate_selection_not_an_annotated_training_dataset", "scope": "Additional frame candidates from existing local videos; no new independent source events.", "inventory_sha256": digest(inventory_path), "groups_sha256": digest(groups_path), "selection_script_sha256": digest(Path(__file__)), "reviewed_reference_images": len(references), "scanned_candidate_frames": len(pool), "target_maximum": 50, "selected_count": len(saved), "selection": "One candidate near the midpoint of each second, then balanced farthest-first coarse DCT selection; maximum 10 per video; distance >8 from reviewed images and earlier selected candidates; at least 1.5 seconds between selected frames within a video.", "limits": ["Full-frame similarity is not a logo-quality score or proof of independent scenes.", "Candidates may contain no target logo or ambiguous logos; no positive or negative labels approved.", "Only the same two provisional event groups; no independent test created.", "Frame times are FPS estimates, not exposure measurements.", "External upload and reuse permissions remain to be documented."], "class_names": ["nox_texto", "nox_simbolo"], "cloud_upload_executed": False, "videos": videos, "images": saved}
    (output / "manifest.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from sample_videos import make_sheet
    index_lines = ["# Candidatos adicionales para revisar variantes NOX", "", "No son positivos aprobados ni un dataset de entrenamiento. Abrir los originales para juzgar el logo.", ""]
    for video_id in videos:
        samples = [{"sample_id": f"C{n:02d}", "image": str(Path(item["source_image"]).relative_to(output.relative_to(root))).replace("\\", "/"), "reference_seconds": item["reference_seconds"], "frame_index": item["frame_index"]} for n, item in enumerate(saved, 1) if item["video_id"] == video_id]
        if samples:
            sheet = make_sheet(samples, output, video_id)
            index_lines += [f"## {video_id}", f"![Hoja de candidatos]({sheet})", ""]
    (output / "index.md").write_text("\n".join(index_lines), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    result = prepare(parser.parse_args().project_root)
    print(json.dumps({"scanned": result["scanned_candidate_frames"], "selected": result["selected_count"], "by_video": {key: sum(item["video_id"] == key for item in result["images"]) for key in result["videos"]}, "approved_labels": 0, "uploaded": False}))
