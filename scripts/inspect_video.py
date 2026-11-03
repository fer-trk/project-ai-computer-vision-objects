"""Read video frames progressively with source presentation timestamps."""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

import cv2


class VideoError(ValueError):
    """Describe an unusable video or an incomplete decode."""


def positive_number(value, name):
    """Reject missing, nonfinite, or nonpositive metadata."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise VideoError(f"{name}: valor no disponible") from exc
    if not math.isfinite(number) or number <= 0:
        raise VideoError(f"{name}: debe ser positivo y finito")
    return number


def probe_video(path):
    """Inspect the first video stream without trusting the file extension."""
    path = Path(path)
    if not path.is_file():
        raise VideoError("No existe el archivo de vídeo")
    executable = shutil.which("ffprobe")
    if executable is None:
        raise VideoError("FFprobe no está disponible en PATH")
    result = subprocess.run(
        [executable, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,duration,avg_frame_rate,nb_frames:format=duration",
         "-of", "json", str(path.resolve())],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30,
    )
    if result.returncode or result.stderr.strip():
        raise VideoError("El archivo no contiene un vídeo legible: " + result.stderr.strip()[:500])
    payload = json.loads(result.stdout)
    if not payload.get("streams"):
        raise VideoError("El archivo no contiene una pista de vídeo")
    stream = payload["streams"][0]
    duration_source = "video_stream"
    duration = stream.get("duration")
    if duration in (None, "N/A"):
        duration = payload.get("format", {}).get("duration")
        duration_source = "container"
    return {
        "width": int(positive_number(stream.get("width"), "Anchura")),
        "height": int(positive_number(stream.get("height"), "Altura")),
        "duration_seconds": positive_number(duration, "Duración"),
        "duration_source": duration_source,
        "average_frame_rate": stream.get("avg_frame_rate"),
        "declared_frame_count": stream.get("nb_frames"),
    }


@contextmanager
def source_timestamps(path):
    """Stream decoded timestamps; close the subprocess on every exit path."""
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [shutil.which("ffprobe"), "-v", "error", "-select_streams", "v:0",
             "-show_frames", "-show_entries",
             "frame=best_effort_timestamp_time,duration_time",
             "-of", "compact=p=0:nk=0", str(Path(path).resolve())],
            stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8",
        )
        try:
            yield process.stdout
            process.wait(timeout=30)
            errors.seek(0)
            message = errors.read(1000).decode("utf-8", errors="replace").strip()
            if process.returncode or message:
                raise VideoError("Decodificación incompleta: " + message)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()


@dataclass
class VideoFrame:
    """Keep one decoded image and its source time, without retaining history."""

    index: int
    source_pts_seconds: float
    timestamp_seconds: float
    declared_duration_seconds: float | None
    image: object


@contextmanager
def open_video(path, *, max_duration_seconds=None, max_pixels=None):
    """Yield metadata and a lazy iterator, releasing decoders even after a break."""
    info = probe_video(path)
    if max_duration_seconds is not None:
        limit = positive_number(max_duration_seconds, "Límite de duración")
        if info["duration_seconds"] > limit:
            raise VideoError("El vídeo supera el límite de duración indicado")
    if max_pixels is not None:
        limit = positive_number(max_pixels, "Límite de píxeles")
        if info["width"] * info["height"] > limit:
            raise VideoError("El vídeo supera el límite de resolución indicado")
    capture = cv2.VideoCapture(str(Path(path).resolve()))
    if not capture.isOpened():
        capture.release()
        raise VideoError("OpenCV no puede abrir el vídeo")

    def frames():
        origin = previous = None
        index = 0
        with source_timestamps(path) as lines:
            for line in lines:
                if not line.strip():
                    continue
                fields = dict(part.split("=", 1) for part in line.strip().split("|") if "=" in part)
                try:
                    pts = float(fields["best_effort_timestamp_time"])
                except (KeyError, ValueError) as exc:
                    raise VideoError("Un fotograma no tiene timestamp válido") from exc
                if not math.isfinite(pts) or (previous is not None and pts <= previous):
                    raise VideoError("Los timestamps no son finitos o estrictamente crecientes")
                if origin is None:
                    origin = pts
                duration = fields.get("duration_time")
                duration = None if duration in (None, "N/A") else positive_number(duration, "Duración de fotograma")
                ok, image = capture.read()
                if not ok or image is None:
                    raise VideoError("OpenCV terminó antes que la pista de vídeo")
                yield VideoFrame(index, pts, pts - origin, duration, image)
                previous = pts
                index += 1
            if not index:
                raise VideoError("El vídeo no contiene fotogramas decodificables")
            if capture.read()[0]:
                raise VideoError("Los decodificadores no coinciden en el número de fotogramas")
            declared = info["declared_frame_count"]
            if declared not in (None, "N/A") and int(declared) != index:
                raise VideoError("El número de fotogramas no coincide con la cabecera")

    iterator = frames()
    try:
        yield info, iterator
    finally:
        iterator.close()
        capture.release()


def inspect_video(path, **limits):
    """Summarize a full decode with constant-size statistics."""
    start = time.perf_counter()
    count = 0
    previous = None
    minimum = maximum = None
    first_pts = last_pts = last_timestamp = None
    with open_video(path, **limits) as (info, frames):
        for frame in frames:
            if first_pts is None:
                first_pts = frame.source_pts_seconds
            if previous is not None:
                delta = frame.timestamp_seconds - previous
                minimum = delta if minimum is None else min(minimum, delta)
                maximum = delta if maximum is None else max(maximum, delta)
            count += 1
            previous = last_timestamp = frame.timestamp_seconds
            last_pts = frame.source_pts_seconds
    return dict(
        info, complete=True, frames_decoded=count,
        first_source_pts_seconds=first_pts, last_source_pts_seconds=last_pts,
        last_timestamp_seconds=last_timestamp,
        minimum_frame_step_seconds=minimum, maximum_frame_step_seconds=maximum,
        elapsed_seconds=time.perf_counter() - start,
        timestamp_method="ffprobe best_effort_timestamp_time; relative to first frame",
    )


def main():
    parser = argparse.ArgumentParser(description="Inspeccionar vídeo sin cargarlo completo en RAM")
    parser.add_argument("video", type=Path)
    parser.add_argument("--max-duration-seconds", type=float)
    parser.add_argument("--max-pixels", type=int)
    args = parser.parse_args()
    try:
        report = inspect_video(args.video, max_duration_seconds=args.max_duration_seconds, max_pixels=args.max_pixels)
    except (VideoError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Error de vídeo: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
