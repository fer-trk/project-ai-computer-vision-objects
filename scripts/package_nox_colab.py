"""Package a verified local dataset for manual transfer to Colab."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def package_dataset(root):
    """Verify bytes and archive only the declared dataset files."""
    root = root.resolve()
    source = root / "data/review/nox-exploratory-dataset-2026-10-26"
    output = root / "data/review/colab-transfer/nox-exploratory-dataset-2026-10-26.zip"
    if output.exists():
        raise FileExistsError("Refusing to overwrite the transfer package")
    manifest_bytes = (source / "manifest.json").read_bytes()
    if manifest_bytes != (root / "docs/nox-exploratory-dataset-2026-10-26.json").read_bytes():
        raise ValueError("Local and published manifests disagree")
    manifest = json.loads(manifest_bytes)
    names = {"manifest.json", "verification.json", "dataset.yaml"}
    for item in manifest["images"]:
        for key, digest_key in (("image", "source_sha256"), ("label", "label_sha256")):
            name = item[key]
            path = (source / name).resolve()
            if not path.is_relative_to(source.resolve()):
                raise ValueError("Dataset path escapes its directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != item[digest_key]:
                raise ValueError("Dataset file hash mismatch")
            names.add(name)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            archive.write(source / name, name)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != names:
            raise ValueError("Archive verification failed")
    print(json.dumps({"archive": str(output), "files": len(names), "images": len(manifest["images"]), "bytes": output.stat().st_size}))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    package_dataset(parser.parse_args().project_root)
