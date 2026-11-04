"""Verify a NOX text run before allowing its checkpoints to be used by T10."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGREED_PARAMETERS = dict(epochs=50, patience=10, imgsz=640, batch=2, seed=42, mosaic=0.0, mixup=0.0, fliplr=0.0, flipud=0.0)
EXPECTED_MODEL = "yolo11n.pt"
EXPECTED_DATASET_ZIP_SHA256 = "8332c1b07824f7c5a2abac9c43f17c23cc78dfa2d7c92d9953af77b4a9364254"
# Exact manifest bytes inside the approved ZIP, rather than its later documentation copy.
EXPECTED_DATASET_MANIFEST_SHA256 = "50d580c88ffb9965cbcbffe82e54cbdb1c2f9aa8a98fd0a7351ef4247eb39608"
REQUIRED = ("train/weights/best.pt", "train/weights/last.pt", "train/args.yaml", "train/results.csv", "experiment.json", "environment.json", "requirements-resolved.txt", "dataset-manifest.json")
DEFAULT_OUTPUT = Path("local-artifacts/nox-text-runs")


def digest(data):
    """SHA-256 of bytes."""
    return hashlib.sha256(data).hexdigest()


def ensure_ignored(path):
    """Refuse destinations that Git would track, without creating them first."""
    probe = Path(path).resolve() / "probe"
    existing = probe.parent
    while not existing.exists():
        existing = existing.parent
    result = subprocess.run(["git", "check-ignore", "-q", "--", str(probe)], cwd=existing, capture_output=True)
    if result.returncode != 0:
        raise ValueError(f"{path} is not ignored by Git; refusing to write results there")


def parameters_match(value):
    """Check agreed numeric values without accepting YAML booleans as numbers."""
    return isinstance(value, dict) and all(
        not isinstance(value.get(key), bool) and value.get(key) == expected
        for key, expected in AGREED_PARAMETERS.items()
    )


def validate_checkpoint(path):
    """Load local weights on CPU and require the single NOX text detection class."""
    path = Path(path).resolve()
    if not path.is_file() or path.suffix.lower() != ".pt" or path.stat().st_size == 0:
        raise ValueError("Checkpoint .pt missing or empty")
    os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / "local-artifacts/ultralytics"))
    os.environ.setdefault("YOLO_OFFLINE", "true")
    os.environ.setdefault("YOLO_AUTOINSTALL", "false")
    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise ValueError("Install requirements-inference.txt to validate checkpoints") from error
    model = YOLO(str(path), task="detect")
    model.to("cpu")
    if model.task != "detect" or model.names != {0: "nox_texto"}:
        raise ValueError("Checkpoint must be a detector with only class 0: nox_texto")
    return {"valid": True, "class_names": model.names, "device": "cpu"}


def verify_results(zip_path, output_root, require_ignored=True):
    """Check integrity and identity, preserve diagnostics and validate both weights."""
    zip_path, output_root = Path(zip_path), Path(output_root)
    if require_ignored:
        ensure_ignored(output_root)
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(name.casefold() for name in names)):
            raise ValueError("Results ZIP has duplicate entries")
        for name in names:
            parts = PurePosixPath(name).parts
            if (not parts or name != PurePosixPath(name).as_posix() or name.startswith("/")
                    or ".." in parts or ":" in name or "\\" in name
                    or any(part.endswith((".", " ")) for part in parts)
                    or any(PureWindowsPath(part).is_reserved() for part in parts)
                    or name == "verification.json"):
                raise ValueError(f"Unsafe path in results ZIP: {name}")
        if archive.testzip() is not None:
            raise ValueError("Results ZIP failed its CRC check")
        if "run-manifest.json" not in names:
            raise ValueError("run-manifest.json is missing")
        manifest = json.loads(archive.read("run-manifest.json"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
            raise ValueError("Invalid run-manifest.json structure")
        if set(names) != set(manifest["files"]) | {"run-manifest.json"}:
            raise ValueError("ZIP entries differ from run-manifest.json")
        for name, expected in manifest["files"].items():
            data = archive.read(name)
            if digest(data) != expected["sha256"] or len(data) != expected["bytes"]:
                raise ValueError(f"Hash mismatch for {name}")
        run_name = manifest["run_name"]
        if not isinstance(run_name, str) or not re.fullmatch(r"nox-text-[0-9]{8}-[0-9]{6}", run_name):
            raise ValueError("Unsafe run name")
        missing = sorted(set(REQUIRED) - set(names))
        experiment = json.loads(archive.read("experiment.json")) if "experiment.json" in names else {}
        if not isinstance(experiment, dict):
            raise ValueError("Invalid experiment.json structure")
        args = yaml.safe_load(archive.read("train/args.yaml")) if "train/args.yaml" in names else {}
        args_match = parameters_match(args)
        experiment_match = parameters_match(experiment.get("parameters"))
        dataset_match = (experiment.get("dataset_zip_sha256") == EXPECTED_DATASET_ZIP_SHA256
                         and "dataset-manifest.json" in names
                         and digest(archive.read("dataset-manifest.json")) == EXPECTED_DATASET_MANIFEST_SHA256)
        model_match = (isinstance(args, dict)
                       and PurePosixPath(str(args.get("model", "")).replace("\\", "/")).name == EXPECTED_MODEL
                       and experiment.get("model") == EXPECTED_MODEL)
        threshold = experiment.get("confidence_threshold")
        rationale = experiment.get("confidence_rationale")
        threshold_recorded = (not isinstance(threshold, bool) and isinstance(threshold, (int, float))
                              and 0 <= threshold <= 1 and isinstance(rationale, str) and bool(rationale.strip()))
        errors = []
        if missing:
            errors.append("Required files are missing")
        if not args_match or not experiment_match:
            errors.append("Training parameters differ from the agreed configuration")
        if not dataset_match:
            errors.append("Dataset identity differs from the approved ZIP or manifest")
        if not model_match:
            errors.append("The run does not identify the agreed YOLO11n source model")
        if not re.fullmatch(r"[0-9a-f]{64}", str(experiment.get("pretrained_checkpoint_sha256", ""))):
            errors.append("The pretrained checkpoint hash is missing or invalid")
        if not threshold_recorded:
            errors.append("A preselected confidence threshold and rationale must be recorded")
        status = experiment.get("status", "unknown")
        if (status != "training_completed" or manifest.get("status") != status
                or experiment.get("run_name") != run_name):
            errors.append("Run identity or completion status is inconsistent")
        error_log_present = "error.log" in names
        if error_log_present or manifest.get("error_log_present") is not False:
            errors.append("An error log is present or its manifest flag is invalid")
        if manifest.get("missing_required") != missing:
            errors.append("The missing-file list is inconsistent")
        target = output_root / run_name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"{target} already exists; not overwriting")
        for name in names:
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(name))
    checkpoints = {}
    # Reject inconsistent metadata before attempting to deserialize a checkpoint.
    if not errors:
        for name in ("train/weights/best.pt", "train/weights/last.pt"):
            try:
                checkpoints[name] = validate_checkpoint(target / name)
            except Exception as error:
                checkpoints[name] = {"valid": False, "error": f"{type(error).__name__}: {error}"}
                errors.append(f"Invalid checkpoint: {name}")
    report = dict(
        run_name=run_name, status=status, complete=not errors, errors=errors,
        missing_required=missing, error_log_present=error_log_present,
        args_match_agreed=args_match, experiment_match_agreed=experiment_match,
        dataset_matches_approved=dataset_match, model_matches_agreed=model_match,
        confidence_selection_recorded=threshold_recorded, checkpoints=checkpoints,
        results_zip_sha256=digest(zip_path.read_bytes()), unpacked_to=str(target),
    )
    (target / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    """Return a nonzero status for rejected or incomplete result packages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_zip", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)
    try:
        report = verify_results(arguments.results_zip, arguments.output)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, yaml.YAMLError) as error:
        print(json.dumps({"complete": False, "error": str(error)}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
