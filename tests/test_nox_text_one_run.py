"""Exercise the NOX text notebook cells and results verifier without a GPU or real data."""

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_nox_text_results as verifier

REAL_SHA = "8332c1b07824f7c5a2abac9c43f17c23cc78dfa2d7c92d9953af77b4a9364254"
PREFIX = "nox-text-2026-11-03/"
YAML_TEXT = "path: /content/nox-text-2026-11-03\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: nox_texto\n"
NOTEBOOK = json.loads((ROOT / "notebooks/nox_text_training.ipynb").read_text(encoding="utf-8"))
CELLS = {c["metadata"]["tags"][0]: "".join(c["source"]) for c in NOTEBOOK["cells"] if c["cell_type"] == "code"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_zip(yaml_text=YAML_TEXT):
    """A 23-image archive in the real layout (19 train, 3 val, 1 test), with tiny synthetic PNGs."""
    entries, images = {}, []
    for i, split in enumerate(["train"] * 19 + ["val"] * 3 + ["test"]):
        buffer = io.BytesIO()
        Image.new("RGB", (64, 48), (i * 10, i * 3, i)).save(buffer, "PNG")
        png = buffer.getvalue()
        positive = i % 4 != 3
        label = b"0 0.375 0.375 0.5 0.5\n" if positive else b""
        name, label_name = f"images/{split}/img{i}.png", f"labels/{split}/img{i}.txt"
        entries[PREFIX + name], entries[PREFIX + label_name] = png, label
        images.append(dict(image=name, label=label_name, source_sha256=sha(png), label_sha256=sha(label), width=64, height=48,
                           boxes=[[8, 6, 40, 30]] if positive else [], split=split, video_id=f"{split}-v{i}", group_id=f"{split}-g"))
    manifest = dict(classes={"0": "nox_texto"}, summary={}, images=images)
    entries[PREFIX + "manifest.json"] = json.dumps(manifest).encode()
    entries[PREFIX + "dataset.yaml"] = yaml_text.encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class Harness:
    """Run notebook cells in a shared namespace with Colab, YOLO and CUDA replaced by stubs."""

    def __init__(self, folder, payload, confirmed=True, last_pt=True, fail_training=False):
        self.folder, self.payload, self.downloads = Path(folder), payload, []
        self.colab = types.ModuleType("google.colab")
        self.colab.files = types.SimpleNamespace(upload=lambda: {"dataset.zip": payload}, download=self.downloads.append)
        harness = self

        class FakeYOLO:
            def __init__(self, checkpoint):
                assert checkpoint == "yolo11n.pt"
                self.ckpt_path = harness.folder / "fake.pt"
                self.ckpt_path.write_bytes(b"stub")

            def train(self, **kwargs):
                if fail_training:
                    raise RuntimeError("simulated CUDA failure")
                weights = Path(kwargs["project"]) / kwargs["name"] / "weights"
                weights.mkdir(parents=True)
                (weights / "best.pt").write_bytes(b"best")
                if last_pt:
                    (weights / "last.pt").write_bytes(b"last")
                (weights.parent / "args.yaml").write_text(yaml.safe_dump(verifier.AGREED_PARAMETERS))
                (weights.parent / "results.csv").write_text("epoch\n1\n")

        self.state = dict(Path=Path, datetime=datetime, timezone=timezone, hashlib=hashlib, io=io, json=json, zipfile=zipfile, time=time,
                          math=__import__("math"), WORK=self.folder / "work", environment={"stub": True}, freeze="stub==1\n", YOLO=FakeYOLO,
                          torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True)))
        self.state["WORK"].mkdir()
        self.confirmed = confirmed

    def run(self, tag, edit=None):
        source = CELLS[tag]
        if tag == "dataset-check":
            source = source.replace(REAL_SHA, sha(self.payload))
            if self.confirmed:
                source = source.replace("PERMISSIONS_CONFIRMED = False", "PERMISSIONS_CONFIRMED = True")
        if edit:
            assert edit[0] in source
            source = source.replace(*edit)
        with patch.dict(sys.modules, {"google.colab": self.colab}):
            exec(source, self.state)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def prepared(self, **kwargs):
        harness = Harness(self.folder, make_zip(), **kwargs)
        harness.run("dataset-check")
        harness.run("experiment-config")
        return harness

    def finished(self, **kwargs):
        harness = self.prepared(**kwargs)
        harness.run("train")
        harness.run("download")
        return harness, Path(harness.downloads[0])


class NotebookTests(Base):

    def test_unconfirmed_permissions_stop_before_upload(self):
        harness = Harness(self.folder, make_zip(), confirmed=False)
        harness.colab.files.upload = lambda: self.fail("upload requested without permissions")
        with self.assertRaises(PermissionError):
            harness.run("dataset-check")
        self.assertFalse((harness.state["WORK"] / "dataset").exists())

    def test_valid_archive_is_verified_and_extracted(self):
        harness = Harness(self.folder, make_zip())
        harness.run("dataset-check")
        config = yaml.safe_load((harness.state["DATA"] / "dataset.yaml").read_text())
        self.assertEqual(config["names"], {0: "nox_texto"})
        self.assertEqual(len(harness.state["manifest"]["images"]), 23)

    def test_wrong_hash_and_wrong_class_yaml_are_rejected_before_extraction(self):
        harness = Harness(self.folder, make_zip())
        harness.colab.files.upload = lambda: {"a.zip": b"not the approved archive"}
        with self.assertRaisesRegex(ValueError, "no coincide"):
            harness.run("dataset-check")
        self.assertFalse((harness.state["WORK"] / "dataset").exists())
        with tempfile.TemporaryDirectory() as folder:
            other = Harness(folder, make_zip(YAML_TEXT.replace("nox_texto", "nox")))
            with self.assertRaisesRegex(ValueError, "nox_texto"):
                other.run("dataset-check")
            self.assertFalse((other.state["WORK"] / "dataset").exists())

    def test_second_run_is_blocked_by_lock(self):
        harness = self.prepared()
        self.assertTrue((harness.state["RUNS"] / "ONE_RUN.lock").is_file())
        with self.assertRaisesRegex(FileExistsError, "un solo run"):
            harness.run("experiment-config")

    def test_edited_parameters_are_rejected_without_burning_the_lock(self):
        harness = Harness(self.folder, make_zip())
        harness.run("dataset-check")
        with self.assertRaisesRegex(ValueError, "barridos"):
            harness.run("experiment-config", edit=("epochs=50", "epochs=100", 1))
        self.assertFalse((harness.state["RUNS"] / "ONE_RUN.lock").exists())

    def test_agreed_configuration_matches_the_verifier_and_notebook(self):
        harness = self.prepared()
        self.assertEqual(harness.state["AGREED"], verifier.AGREED_PARAMETERS)
        for key, value in verifier.AGREED_PARAMETERS.items():
            self.assertEqual(harness.state["PARAMETERS"][key], value)

    def test_failed_training_leaves_error_log(self):
        harness = self.prepared(fail_training=True)
        with self.assertRaises(RuntimeError):
            harness.run("train")
        run = harness.state["RUN"]
        self.assertIn("simulated CUDA failure", (run / "error.log").read_text())
        self.assertEqual(json.loads((run / "experiment.json").read_text())["status"], "training_failed_or_interrupted")

class ResultsTests(Base):
    def test_complete_run_is_verified_and_unpacked(self):
        harness, archive = self.finished()
        report = verifier.verify_results(archive, self.folder / "out", require_ignored=False)
        self.assertTrue(report["complete"])
        self.assertTrue(report["args_match_agreed"])
        self.assertEqual(report["missing_required"], [])
        self.assertTrue((self.folder / "out" / report["run_name"] / "train/weights/best.pt").is_file())
        with self.assertRaises(FileExistsError):
            verifier.verify_results(archive, self.folder / "out", require_ignored=False)

    def test_missing_checkpoint_is_reported_incomplete(self):
        _, archive = self.finished(last_pt=False)
        report = verifier.verify_results(archive, self.folder / "out", require_ignored=False)
        self.assertFalse(report["complete"])
        self.assertEqual(report["missing_required"], ["train/weights/last.pt"])

    def test_tampered_file_is_rejected(self):
        _, archive = self.finished()
        tampered = self.folder / "tampered.zip"
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(tampered, "w") as target:
            for item in source.infolist():
                data = source.read(item.filename)
                target.writestr(item.filename, b"changed" if item.filename.endswith("best.pt") else data)
        with self.assertRaisesRegex(ValueError, "Hash mismatch"):
            verifier.verify_results(tampered, self.folder / "out", require_ignored=False)
        self.assertFalse((self.folder / "out").exists())

    def test_unsafe_path_is_rejected(self):
        bad = self.folder / "bad.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("../evil.txt", "x")
        with self.assertRaisesRegex(ValueError, "Unsafe path"):
            verifier.verify_results(bad, self.folder / "out", require_ignored=False)

    def test_destination_must_be_ignored_by_git(self):
        _, archive = self.finished()
        repo = self.folder / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        (repo / ".gitignore").write_text("local-artifacts/\n")
        with self.assertRaisesRegex(ValueError, "not ignored"):
            verifier.verify_results(archive, repo / "tracked")
        report = verifier.verify_results(archive, repo / "local-artifacts/nox-text-runs")
        self.assertTrue(report["complete"])


if __name__ == "__main__":
    unittest.main()
