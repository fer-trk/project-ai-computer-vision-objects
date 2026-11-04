"""Check the synthetic generator: determinism, box validity and validator safeguards."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import generate_nox_synthetic as synthetic

COUNTS = dict(diag_train=(3, 5), diag_val=(3, 5))


class SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.summary = synthetic.build(cls.root / "a", 7, COUNTS)
        cls.manifest = json.loads((cls.root / "a/manifest.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_counts_and_flags(self):
        self.assertEqual(self.summary["diag_train"]["positives"], 3)
        self.assertEqual(self.summary["diag_val"]["negatives"], 5)
        self.assertTrue(self.manifest["synthetic"])
        self.assertFalse(self.manifest["official_dataset_mixing"])
        self.assertTrue(all(r["synthetic"] for r in self.manifest["images"]))
        self.assertEqual(self.manifest["seed"], 7)

    def test_positive_boxes_inside_image_and_negatives_empty(self):
        for record in self.manifest["images"]:
            rows = (self.root / "a" / record["label"]).read_text(encoding="utf-8").splitlines()
            if record["positive"]:
                self.assertGreaterEqual(len(rows), 1)
                for box in record["boxes"]:
                    x1, y1, x2, y2 = box["bbox_xyxy"]
                    self.assertTrue(0 <= x1 < x2 <= record["width"] and 0 <= y1 < y2 <= record["height"])
                    self.assertGreaterEqual(box["visible_fraction"], synthetic.MIN_VISIBLE_FRACTION)
            else:
                self.assertEqual(rows, [])

    def test_same_seed_reproduces_hashes_and_other_seed_differs(self):
        synthetic.build(self.root / "b", 7, COUNTS)
        synthetic.build(self.root / "c", 8, COUNTS)
        hashes = lambda name: [r["image_sha256"] for r in json.loads((self.root / name / "manifest.json").read_text(encoding="utf-8"))["images"]]
        self.assertEqual(hashes("a"), hashes("b"))
        self.assertNotEqual(hashes("a"), hashes("c"))

    def test_validate_accepts_clean_set(self):
        self.assertEqual(synthetic.validate(self.root / "a")["images"], 16)

    def test_validate_rejects_tampering(self):
        synthetic.build(self.root / "d", 7, COUNTS)
        record = next(r for r in self.manifest["images"] if r["positive"])
        label = self.root / "d" / record["label"]
        label.write_text("0 0.5 0.5 1.5 0.2\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            synthetic.validate(self.root / "d")

    def test_validate_rejects_box_on_negative(self):
        synthetic.build(self.root / "e", 7, COUNTS)
        record = next(r for r in self.manifest["images"] if not r["positive"])
        (self.root / "e" / record["label"]).write_text("0 0.5 0.5 0.2 0.1\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            synthetic.validate(self.root / "e")

    def test_refuses_to_overwrite(self):
        with self.assertRaises(FileExistsError):
            synthetic.build(self.root / "a", 7, COUNTS)

    def test_reserved_font_not_used_in_positive_training_examples(self):
        for record in self.manifest["images"]:
            if record["split"] == "diag_train" and record["positive"]:
                for item in record["transformations"].get("prints", []):
                    self.assertNotEqual(item["font"], synthetic.VAL_ONLY_FONT)

    def test_yolo_row_round_trip(self):
        row = synthetic.yolo_row([20, 10, 60, 30], (100, 50))
        self.assertEqual([round(float(v), 6) for v in row.split()[1:]], [0.4, 0.4, 0.4, 0.4])

    def test_cli_default_generates_from_fresh_checkout_without_touching_reference(self):
        repo = self.root / "fresh-checkout"
        script = repo / "scripts/generate_nox_synthetic.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(synthetic.__file__, script)
        reference = repo / "data-synthetic/nox-text-diagnostic/manifest.json"
        reference.parent.mkdir(parents=True)
        reference.write_bytes(b"versioned reference must remain unchanged\n")
        command = [sys.executable, str(script), "--train", "1", "1", "--val", "1", "1"]
        result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = repo / "local-artifacts/nox-text-diagnostic"
        self.assertEqual(synthetic.validate(output)["images"], 4)
        self.assertEqual(reference.read_bytes(), b"versioned reference must remain unchanged\n")
        before = (output / "manifest.json").read_bytes()
        validated = subprocess.run([sys.executable, str(script), "--validate-only"], cwd=repo,
                                   capture_output=True, text=True, timeout=120)
        self.assertEqual(validated.returncode, 0, validated.stderr)
        repeated = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertIn("Refusing to overwrite", repeated.stderr)
        self.assertEqual((output / "manifest.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
