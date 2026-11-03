"""Validate the Colab handoff offline; never run actual model training."""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import types
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset_zip", type=Path)
parser.add_argument("--nbformat-path", type=Path)
args = parser.parse_args()
if args.nbformat_path:
    sys.path.insert(0, str(args.nbformat_path))
import nbformat
import torch
import yaml
from ultralytics.cfg import DEFAULT_CFG_DICT, get_cfg
from ultralytics.data.dataset import YOLODataset
from ultralytics.data.utils import check_det_dataset

root = Path(__file__).resolve().parents[1]
notebook = nbformat.read(root / "notebooks/nox_text_training.ipynb", as_version=4)
nbformat.validate(notebook)
cells = {}
for cell in notebook.cells:
    if cell.cell_type == "code":
        ast.parse(cell.source)
        assert cell.execution_count is None and not cell.outputs
        cells[cell.metadata.tags[0]] = cell.source
assert len(cells) == 8

archive_bytes = args.dataset_zip.read_bytes()
stub = types.ModuleType("google.colab")
stub.files = types.SimpleNamespace(upload=lambda: {args.dataset_zip.name: archive_bytes})
sys.modules["google.colab"] = stub
checks = ["nbformat schema", "8 code cells: syntax and empty outputs"]
with tempfile.TemporaryDirectory(prefix="nox-notebook-") as folder:
    state = dict(Path=Path, datetime=datetime, timezone=timezone, hashlib=hashlib,
                 io=io, json=json, math=math, zipfile=zipfile, time=time,
                 WORK=Path(folder), environment={"validation": "offline"}, freeze="offline validation\n")
    for invalid in ({}, {"a.zip": b"wrong"}, {"a": archive_bytes, "b": archive_bytes}):
        stub.files.upload = lambda payload=invalid: payload
        try:
            exec(cells["dataset-check"], state)
        except ValueError:
            assert not (Path(folder) / "dataset").exists()
        else:
            raise AssertionError("Invalid upload was accepted")
    checks.append("missing/multiple/wrong-hash uploads rejected before extraction")
    stub.files.upload = lambda: {args.dataset_zip.name: archive_bytes}
    exec(cells["dataset-check"], state)
    checks.append("real ZIP: 23 image/label hashes, dimensions, boxes and group separation")
    try:
        exec(cells["dataset-check"], state)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing dataset was overwritten")
    checked = check_det_dataset(str(state["DATA"] / "dataset.yaml"), autodownload=False)
    assert checked["names"] == {0: "nox_texto"}
    for split, count in (("train", 19), ("val", 3), ("test", 1)):
        loaded = YOLODataset(img_path=checked[split], data=checked, imgsz=640,
                             batch_size=2, augment=False, cache=False, prefix=split+": ")
        assert len(loaded) == count and len(loaded.labels) == count
    checks.append("Ultralytics real loader: train 19 / val 3 / test 1")
    exec(cells["experiment-config"], state)
    get_cfg(DEFAULT_CFG_DICT, overrides=state["PARAMETERS"])
    checks.append("training parameters accepted by installed Ultralytics")

    class FakeYOLO:
        def __init__(self, checkpoint):
            assert checkpoint == "yolo11n.pt"
            self.ckpt_path = Path(folder) / "fake-pretrained.pt"
            self.ckpt_path.write_bytes(b"offline stub, not model weights")

        def train(self, **kwargs):
            assert kwargs["data"] == str(state["DATA"] / "dataset.yaml")
            for key, value in state["PARAMETERS"].items():
                assert kwargs[key] == value
            target = Path(kwargs["project"]) / kwargs["name"] / "weights/best.pt"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"offline stub, not model weights")

    state.update(YOLO=FakeYOLO, torch=types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: True)))
    exec(cells["train"], state)
    record = json.loads((state["RUN"] / "experiment.json").read_text())
    assert record["status"] == "training_completed"
    assert record["dataset_zip_sha256"] == state["EXPECTED_ZIP"]
    assert record["parameters"]["epochs"] == 50 and record["parameters"]["patience"] == 10
    checks.append("mock training orchestration and artifact metadata; no training performed")
    downloads = []
    stub.files.download = downloads.append
    exec(cells["download"], state)
    with zipfile.ZipFile(downloads[0]) as exported:
        assert exported.testzip() is None
        assert {"experiment.json", "environment.json", "dataset-manifest.json", "train/weights/best.pt"} <= set(exported.namelist())
    checks.append("result archive, CRC and download invocation with temporary mock artifacts")

if not torch.cuda.is_available():
    try:
        exec(cells["gpu-check"], {})
    except RuntimeError as error:
        assert "No hay GPU CUDA" in str(error)
    else:
        raise AssertionError("CPU guard did not stop execution")
    checks.append("CPU-only host correctly refuses Colab training")
print(json.dumps({"passed": checks, "not_executed": ["Colab installation and GPU runtime", "actual training and evaluation", "browser upload/download in Colab"]}, indent=2))
