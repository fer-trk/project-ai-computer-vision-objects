"""Test real CPU loading in subprocesses so Ultralytics patches cannot leak."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
AVAILABLE = importlib.util.find_spec("ultralytics") is not None and importlib.util.find_spec("torch") is not None
PREPARE = '''
from pathlib import Path
import sys
import ultralytics
from ultralytics import YOLO
import yaml
root = Path(sys.argv[1])
config = yaml.safe_load((Path(ultralytics.__file__).parent / "cfg/models/11/yolo11.yaml").read_text())
config.update(nc=1, scale="n")
path = root / "yolo11n-fixture.yaml"
path.write_text(yaml.safe_dump(config), encoding="utf-8")
model = YOLO(str(path), task="detect", verbose=False)
model.model.names = {0: "nox_texto"}
model.save(root / "best.pt")
model.model.names = {0: "another_class"}
model.save(root / "wrong-class.pt")
'''
VALIDATE = '''
import json, sys
sys.path.insert(0, sys.argv[1])
from verify_nox_text_results import validate_checkpoint
try:
    report = validate_checkpoint(sys.argv[2])
except Exception as error:
    print(json.dumps({"valid": False, "error": str(error)}))
    raise SystemExit(2)
print(json.dumps(report))
'''


@unittest.skipUnless(AVAILABLE, "Install requirements-inference.txt for real checkpoint loading tests")
class CheckpointLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.env = dict(os.environ, YOLO_CONFIG_DIR=str(cls.root / "settings"),
                       YOLO_OFFLINE="true", YOLO_AUTOINSTALL="false")
        result = subprocess.run([sys.executable, "-c", PREPARE, str(cls.root)], env=cls.env,
                                capture_output=True, text=True, timeout=120)
        if result.returncode:
            cls.temporary.cleanup()
            raise AssertionError(result.stderr)
        (cls.root / "corrupt.pt").write_bytes(b"best")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def load(self, filename):
        result = subprocess.run([sys.executable, "-c", VALIDATE, str(SCRIPTS), str(self.root / filename)],
                                env=self.env, capture_output=True, text=True, timeout=120)
        return result.returncode, json.loads(result.stdout.strip().splitlines()[-1])

    def test_real_untrained_checkpoint_can_be_loaded_on_cpu(self):
        code, report = self.load("best.pt")
        self.assertEqual(code, 0)
        self.assertTrue(report["valid"])
        self.assertEqual(report["class_names"], {"0": "nox_texto"})
        self.assertEqual(report["device"], "cpu")

    def test_garbage_bytes_are_not_a_checkpoint(self):
        code, report = self.load("corrupt.pt")
        self.assertEqual(code, 2)
        self.assertFalse(report["valid"])
        self.assertTrue(report["error"])

    def test_loadable_checkpoint_with_other_class_is_rejected(self):
        code, report = self.load("wrong-class.pt")
        self.assertEqual(code, 2)
        self.assertFalse(report["valid"])
        self.assertIn("nox_texto", report["error"])
