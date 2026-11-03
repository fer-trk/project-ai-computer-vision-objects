"""Verify a downloaded NOX text results ZIP and unpack it into an ignored folder."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

import yaml

AGREED_PARAMETERS = dict(epochs=50, patience=10, imgsz=640, batch=2, seed=42, mosaic=0.0, mixup=0.0, fliplr=0.0, flipud=0.0)
REQUIRED = ("train/weights/best.pt", "train/weights/last.pt", "train/args.yaml", "train/results.csv", "experiment.json", "environment.json", "requirements-resolved.txt", "dataset-manifest.json")
DEFAULT_OUTPUT = Path("local-artifacts/nox-text-runs")


def digest(data):
    """SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def ensure_ignored(path):
    """Refuse destinations that Git would track."""
    probe = Path(path).resolve() / "probe"
    result = subprocess.run(["git", "check-ignore", "-q", str(probe)], cwd=probe.parent if probe.parent.exists() else Path.cwd())
    if result.returncode != 0:
        raise ValueError(f"{path} is not ignored by Git; refusing to write results there")


def verify_results(zip_path, output_root, require_ignored=True):
    """Check CRC, manifest hashes and agreed arguments, then unpack to a new folder."""
    zip_path, output_root = Path(zip_path), Path(output_root)
    if require_ignored:
        output_root.mkdir(parents=True, exist_ok=True)
        ensure_ignored(output_root)
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Results ZIP failed its CRC check")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Results ZIP has duplicate entries")
        for name in names:
            parts = PurePosixPath(name).parts
            if name.startswith("/") or ".." in parts or ":" in name:
                raise ValueError(f"Unsafe path in results ZIP: {name}")
        if "run-manifest.json" not in names:
            raise ValueError("run-manifest.json is missing")
        manifest = json.loads(archive.read("run-manifest.json"))
        if set(names) != set(manifest["files"]) | {"run-manifest.json"}:
            raise ValueError("ZIP entries differ from run-manifest.json")
        for name, expected in manifest["files"].items():
            data = archive.read(name)
            if digest(data) != expected["sha256"] or len(data) != expected["bytes"]:
                raise ValueError(f"Hash mismatch for {name}")
        run_name = manifest["run_name"]
        if not run_name.replace("-", "").isalnum():
            raise ValueError("Unsafe run name")
        missing = sorted(set(REQUIRED) - set(names))
        status = json.loads(archive.read("experiment.json"))["status"] if "experiment.json" in names else "unknown"
        args_match = None
        if "train/args.yaml" in names:
            args = yaml.safe_load(archive.read("train/args.yaml"))
            args_match = all(args.get(key) == value for key, value in AGREED_PARAMETERS.items())
        target = output_root / run_name
        if target.exists():
            raise FileExistsError(f"{target} already exists; not overwriting")
        for name in names:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
    report = dict(run_name=run_name, status=status, complete=not missing and status == "training_completed" and not manifest["error_log_present"], missing_required=missing, error_log_present=manifest["error_log_present"], args_match_agreed=args_match, results_zip_sha256=digest(zip_path.read_bytes()), unpacked_to=str(target))
    (target / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_zip", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    print(json.dumps(verify_results(arguments.results_zip, arguments.output), indent=2))
