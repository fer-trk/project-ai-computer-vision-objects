"""Create a reproducible visual sample for manual video review."""

import argparse
import hashlib
import importlib.metadata
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont


def file_hash(path):
    """Identify the exact source file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clock_label(seconds):
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remainder:06.3f}"


def make_sheet(samples, output_root, video_id):
    """Build thumbnails while preserving separate full-resolution PNGs."""
    columns, tile_width, tile_height = 4, 256, 496
    rows = math.ceil(len(samples) / columns)
    sheet = Image.new("RGB", (columns * tile_width, rows * tile_height), "#121a28")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=15)
    for position, sample in enumerate(samples):
        x = (position % columns) * tile_width
        y = (position // columns) * tile_height
        with Image.open(output_root / sample["image"]) as source:
            preview = source.copy()
        preview.thumbnail((tile_width - 12, tile_height - 44))
        sheet.paste(preview, (x + (tile_width - preview.width) // 2, y + 4))
        label = f"{sample['sample_id']} | {clock_label(sample['reference_seconds'])}"
        draw.text((x + 7, y + tile_height - 34), label, font=font, fill="white")
        draw.text((x + 7, y + tile_height - 17), f"frame {sample['frame_index']}", font=font, fill="#aebdd0")
    destination = output_root / "sheets" / f"{video_id}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=92)
    return destination.relative_to(output_root).as_posix()


def sample_video(path, output_root, count, requested_times=None):
    """Decode sequentially and sample frame bins or requested decoder times."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {path.name}")
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if frame_count < 1 or (requested_times is None and frame_count < count) or not math.isfinite(fps) or fps <= 0:
        capture.release()
        raise RuntimeError(f"Invalid frame count or frame rate: {path.name}")
    targets = {min(frame_count - 1, int((index + 0.5) * frame_count / count)) for index in range(count)}
    expected_samples = len(requested_times) if requested_times is not None else count
    next_time = 0
    frame_dir = output_root / "frames" / path.stem
    frame_dir.mkdir(parents=True, exist_ok=True)
    samples = []
    decoded = 0
    dimensions = None
    previous_timestamp = -1.0
    try:
        while True:
            success, frame = capture.read()
            if not success:
                break
            reported_seconds = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000
            usable_timestamp = math.isfinite(reported_seconds) and reported_seconds >= 0 and reported_seconds > previous_timestamp
            seconds = reported_seconds if usable_timestamp else decoded / fps
            basis = "decoder_pos_msec" if usable_timestamp else "frame_index_over_reported_fps_estimate"
            previous_timestamp = seconds
            take_frame = decoded in targets if requested_times is None else next_time < len(requested_times) and seconds >= requested_times[next_time]
            if take_frame:
                height, width = frame.shape[:2]
                dimensions = [width, height]
                prefix = "S" if requested_times is None else "T"
                sample_id = f"{prefix}{len(samples) + 1:02d}"
                destination = frame_dir / f"{sample_id}_frame_{decoded:06d}.png"
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                image.save(destination)
                samples.append({
                    "sample_id": sample_id,
                    "frame_index": decoded,
                    "reference_seconds": round(seconds, 6),
                    "timestamp_basis": basis,
                    "decoder_pos_msec": round(reported_seconds * 1000, 6) if math.isfinite(reported_seconds) else None,
                    "width": width,
                    "height": height,
                    "image": destination.relative_to(output_root).as_posix(),
                    "requested_seconds": requested_times[next_time] if requested_times is not None else None,
                })
                if requested_times is not None:
                    next_time += 1
            decoded += 1
    finally:
        capture.release()
    if len(samples) != expected_samples or decoded != frame_count:
        raise RuntimeError(f"Decode mismatch for {path.name}: decoded={decoded}, reported={frame_count}, samples={len(samples)}")
    metadata_path = path.with_suffix(".info.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    return {
        "video_id": path.stem,
        "filename": path.name,
        "sha256": file_hash(path),
        "source_url": metadata.get("webpage_url"),
        "download_metadata_duration_seconds": metadata.get("duration"),
        "decoded_frames": decoded,
        "reported_fps": fps,
        "frame_count_over_fps_seconds_estimate": round(decoded / fps, 6),
        "decoded_dimensions": dimensions,
        "samples": samples,
        "sheet": make_sheet(samples, output_root, path.stem),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--review-plan", "--windows-file", dest="review_plan", type=Path, help="JSON file with selected videos and requested times or candidate windows")
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    root = args.root.resolve()
    sources = sorted((root / "data" / "raw" / "videos").glob("*.mp4"))
    if not sources:
        raise RuntimeError("No MP4 source videos found")
    window_plan = None
    if args.review_plan:
        window_plan = json.loads(args.review_plan.read_text(encoding="utf-8-sig"))
        missing = set(window_plan["videos"]) - {source.stem for source in sources}
        if missing:
            raise ValueError(f"Selected source videos are missing: {sorted(missing)}")
        sources = [source for source in sources if source.stem in window_plan["videos"]]
    run_name = window_plan.get("run_name", "targeted-2026-10-21") if window_plan else "initial-2026-10-21"
    if not run_name or run_name in (".", "..") or "/" in run_name or "\\" in run_name:
        raise ValueError("Run name must be one directory name")
    output_root = root / "data" / "review" / run_name
    output_root.mkdir(parents=True, exist_ok=True)
    videos = []
    for source in sources:
        requested_times = None
        if window_plan:
            selection = window_plan["videos"][source.stem]
            if "requested_seconds" in selection:
                requested_times = [float(value) for value in selection["requested_seconds"]]
                if any(not math.isfinite(value) or value < 0 for value in requested_times):
                    raise ValueError("Requested times must be finite and nonnegative")
            else:
                step = float(window_plan["step_seconds"])
                if not math.isfinite(step) or step <= 0:
                    raise ValueError("Sampling step must be finite and positive")
                requested_times = []
                for start, end in selection["windows_seconds"]:
                    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
                        raise ValueError("Invalid candidate window")
                    current = start + step / 2
                    while current < end:
                        requested_times.append(round(current, 6))
                        current += step
            requested_times = sorted(set(requested_times))
            if not requested_times:
                raise ValueError("Candidate windows produced no sample targets")
        video = sample_video(source, output_root, args.samples, requested_times)
        videos.append(video)
        print(f"{source.stem}: {len(video['samples'])} samples, {video['decoded_frames']} decoded frames", flush=True)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sampling": "first decoded frame at or after requested review times; not exposure measurement" if window_plan else "one frame at the center of each equal frame-index bin; not exposure measurement",
        "window_plan": window_plan,
        "script_sha256": file_hash(Path(__file__)),
        "versions": {name: importlib.metadata.version(name) for name in ("opencv-python-headless", "Pillow", "numpy")},
        "sample_count": sum(len(video["samples"]) for video in videos),
        "videos": videos,
    }
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    title = window_plan.get("title", "# Muestra dirigida para revisión") if window_plan else "# Muestra inicial de revisión"
    index = [title, "", "Las miniaturas no sirven para juzgar logos pequeños: abrir el PNG a resolución completa. Son candidatos; no son positivos aprobados ni un dataset final.", ""]
    for video in videos:
        index.extend([f"## {video['video_id']}", "", f"![Hoja de contacto]({video['sheet']})", "", "| Muestra | Frame | Instante solicitado | Referencia decodificada | Imagen completa |", "| --- | --- | --- | --- | --- |"])
        for sample in video["samples"]:
            requested = clock_label(sample["requested_seconds"]) if sample["requested_seconds"] is not None else "—"
            index.append(f"| {sample['sample_id']} | {sample['frame_index']} | {requested} | {clock_label(sample['reference_seconds'])} | [PNG]({sample['image']}) |")
        index.append("")
    (output_root / "index.md").write_text("\n".join(index), encoding="utf-8")
    print(f"Manifest: {output_root / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
