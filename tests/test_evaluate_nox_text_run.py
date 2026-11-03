"""Check the one-run evaluation guards and exports without a real model."""

import contextlib
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_nox_text_run import (
    EvaluationError, ROOT, build_parser, build_report, git_ignores, run_evaluation,
)
from predict_image import PredictionError, file_hash

CLASSES = {0: "nox_texto"}


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name)
        self.root = self.tmp / "repo"
        self.dataset = self.tmp / "dataset"
        for split, name in (("test", "a.png"), ("test", "b.png"), ("train", "c.png"), ("val", "d.png")):
            (self.dataset / "images" / split).mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 48), "white").save(self.dataset / "images" / split / name)
        self.entries = [
            self.entry("test", "a.png", "hash-a", boxes=[[1, 1, 20, 20]]),
            self.entry("test", "b.png", "hash-b"),
            self.entry("train", "c.png", "hash-c"),
            self.entry("val", "d.png", "hash-d"),
        ]
        self.checkpoint = self.tmp / "best.pt"
        self.checkpoint.write_bytes(b"controlled-checkpoint-fixture-not-a-model")
        self.output = self.root / "local-artifacts" / "run"
        self.manifest = self.write_manifest()

    @staticmethod
    def entry(split, name, digest, boxes=()):
        return {"image": f"images/{split}/{name}", "split": split, "source_sha256": digest,
                "width": 64, "height": 48, "boxes": list(boxes)}

    def write_manifest(self, entries=None, classes=None):
        path = self.tmp / "manifest.json"
        path.write_text(json.dumps({
            "classes": {"0": "nox_texto"} if classes is None else classes,
            "status": "fixture", "independent_blind_test": False,
            "limitations": ["fixture limitation"], "images": self.entries if entries is None else entries,
        }), encoding="utf-8")
        return path

    def predictor(self, calls=None):
        """Detect on the first image of a run only; record calls when requested."""
        seen = [] if calls is None else calls
        def controlled(checkpoint, image, **options):
            seen.append(1)
            first = len(seen) == 1
            boxes = [{"bbox_xyxy": [2, 3, 30, 20], "class_id": 0, "confidence": .8},
                     {"bbox_xyxy": [40, 10, 60, 40], "class_id": 0, "confidence": .3}] if first else []
            return CLASSES, boxes
        return controlled

    def evaluate(self, **overrides):
        options = dict(
            checkpoint=self.checkpoint, images_dir=self.dataset, manifest=self.manifest, output=self.output,
            confidence=.25, predictor=self.predictor(), class_reader=lambda checkpoint: CLASSES,
            root=self.root, ignore_check=lambda path, root: True,
        )
        options.update(overrides)
        return run_evaluation(**options)

    def test_confidence_is_mandatory(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["run", "--checkpoint", "c.pt", "--images-dir", "i", "--manifest", "m", "--output", "o"])
        with self.assertRaises(EvaluationError):
            self.evaluate(confidence=None)
        with self.assertRaises(PredictionError):
            self.evaluate(confidence=float("nan"))
        self.assertFalse(self.output.exists())

    def test_missing_checkpoint_blocks_before_prediction(self):
        calls = []
        self.checkpoint.unlink()
        with self.assertRaises(EvaluationError):
            self.evaluate(predictor=self.predictor(calls))
        self.assertEqual(calls, [])
        self.assertFalse(self.output.exists())

    def test_wrong_or_unverifiable_class_blocks_before_prediction(self):
        def unreadable(checkpoint):
            raise EvaluationError("controlled failure")
        calls = []
        for reader in (lambda checkpoint: {0: "nox"}, lambda checkpoint: {0: "nox_texto", 1: "nox_simbolo"}, lambda checkpoint: {}, unreadable):
            with self.subTest(reader=reader), self.assertRaises(EvaluationError):
                self.evaluate(class_reader=reader, predictor=self.predictor(calls))
        self.assertEqual(calls, [])
        self.assertFalse(self.output.exists())

    def test_manifest_with_other_classes_is_blocked(self):
        with self.assertRaises(EvaluationError):
            self.evaluate(manifest=self.write_manifest(classes={"0": "nox"}))

    def test_synthetic_paths_and_flags_are_blocked(self):
        synthetic = self.tmp / "data-synthetic" / "set"
        shutil.copytree(self.dataset, synthetic)
        with self.assertRaises(EvaluationError):
            self.evaluate(images_dir=synthetic)
        flagged = [dict(self.entries[0], synthetic=True)] + self.entries[1:]
        with self.assertRaises(EvaluationError):
            self.evaluate(manifest=self.write_manifest(flagged))
        self.assertFalse(self.output.exists())

    def test_path_traversal_outside_images_dir_is_blocked(self):
        escaping = [dict(self.entries[0], image="../manifest.json")] + self.entries[1:]
        with self.assertRaises(EvaluationError):
            self.evaluate(manifest=self.write_manifest(escaping))

    def test_missing_or_leaking_reserved_partition_is_blocked(self):
        for entries in (self.entries[2:], self.entries[:2] + [dict(self.entries[2], source_sha256="hash-a")]):
            with self.subTest(entries=len(entries)), self.assertRaises(EvaluationError):
                self.evaluate(manifest=self.write_manifest(entries))
        self.assertFalse(self.output.exists())

    def test_explicit_list_only_accepts_reserved_images(self):
        report = self.evaluate(image_names=["b.png"])
        self.assertEqual([row["image"] for row in report["images"]], ["images/test/b.png"])
        for names in (["c.png"], ["d.png"], ["missing.png"], ["a.png", "a.png"]):
            with self.subTest(names=names), self.assertRaises(EvaluationError):
                self.evaluate(image_names=names, output=self.root / "local-artifacts" / "other")

    def test_output_must_be_ignored_and_in_review_folders(self):
        with self.assertRaises(EvaluationError):
            self.evaluate(ignore_check=lambda path, root: False)
        with self.assertRaises(EvaluationError):
            self.evaluate(output=self.root / "docs" / "run")
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / "docs").exists())

    def test_real_git_rules_ignore_review_folders_but_not_docs(self):
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        self.assertTrue(git_ignores(ROOT / "local-artifacts" / "t10-check", ROOT))
        self.assertTrue(git_ignores(ROOT / "data" / "review" / "t10-check", ROOT))
        self.assertFalse(git_ignores(ROOT / "docs" / "t10-check", ROOT))

    def test_existing_output_is_preserved(self):
        self.output.mkdir(parents=True)
        (self.output / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.evaluate()
        self.assertEqual((self.output / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_images_with_and_without_detections_keep_json_and_csv_consistent(self):
        before = {name: file_hash(path) for name, path in (("a", self.dataset / "images/test/a.png"), ("b", self.dataset / "images/test/b.png"))}
        run = self.evaluate()
        self.assertEqual(run["totals"], {"images": 2, "detections": 2, "images_with_detections": 1, "images_without_detections": 1})
        self.assertEqual(before["a"], file_hash(self.dataset / "images/test/a.png"))
        with (self.output / "summary.csv").open(newline="", encoding="utf-8") as handle:
            summary = list(csv.DictReader(handle))
        with (self.output / "detections.csv").open(newline="", encoding="utf-8") as handle:
            detections = list(csv.DictReader(handle))
        self.assertEqual([row["status"] for row in summary], ["detections", "no_detections"])
        self.assertEqual(summary[0]["annotated_boxes"], "1")
        for row in summary:
            persisted = json.loads((self.output / row["predictions_json"]).read_text(encoding="utf-8"))
            self.assertTrue((self.output / row["annotated_png"]).is_file())
            self.assertEqual(persisted["detection_count"], int(row["detection_count"]))
            self.assertEqual(persisted["image"]["sha256"], row["image_sha256"])
            self.assertEqual((persisted["image"]["width"], persisted["image"]["height"]), (int(row["width"]), int(row["height"])))
            self.assertEqual(persisted["model"]["sha256"], file_hash(self.checkpoint))
            rows = [d for d in detections if d["image"] == row["image"]]
            self.assertEqual(len(rows), persisted["detection_count"])
            for csv_row, detection in zip(rows, persisted["detections"], strict=True):
                self.assertEqual(csv_row["class_name"], detection["class_name"])
                self.assertEqual(float(csv_row["confidence"]), detection["confidence"])
                self.assertEqual([float(csv_row[key]) for key in ("x1", "y1", "x2", "y2")], detection["bbox_xyxy"])
        self.assertEqual(json.loads((self.output / "run.json").read_text(encoding="utf-8"))["images"][1]["detection_count"], 0)

    def test_dimension_mismatch_with_manifest_publishes_nothing(self):
        wrong = [dict(self.entries[0], width=99)] + self.entries[1:]
        with self.assertRaises(EvaluationError):
            self.evaluate(manifest=self.write_manifest(wrong))
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.glob(".evaluation-*")), [])

    def fill_review(self, **changes):
        template = json.loads((self.output / "review-template.json").read_text(encoding="utf-8"))
        template.update(reviewed=True, reviewer="Fer")
        template["images"][0]["detections"][0]["verdict"] = "true_positive"
        template["images"][0]["detections"][1]["verdict"] = "false_positive"
        template["images"][0]["missed_logos"] = 0
        template["images"][1]["missed_logos"] = 2
        template["images"][1]["notes"] = "two | logos"
        template.update(changes)
        (self.output / "review.json").write_text(json.dumps(template), encoding="utf-8")

    def test_report_requires_a_complete_matching_manual_review(self):
        self.evaluate(confidence_rationale="chosen by the reviewer")
        pending = dict(ignore_check=lambda path, root: True, root=self.root)
        shutil.copy(self.output / "review-template.json", self.output / "review.json")
        with self.assertRaises(EvaluationError):
            build_report(self.output, **pending)
        self.fill_review(checkpoint_sha256="0" * 64)
        with self.assertRaises(EvaluationError):
            build_report(self.output, **pending)
        self.fill_review()
        review = json.loads((self.output / "review.json").read_text(encoding="utf-8"))
        review["images"][1]["missed_logos"] = None
        (self.output / "review.json").write_text(json.dumps(review), encoding="utf-8")
        with self.assertRaises(EvaluationError):
            build_report(self.output, **pending)
        self.assertFalse((self.output / "report.json").exists())

    def test_report_counts_reviewed_results_without_ratios(self):
        self.evaluate(confidence_rationale="chosen by the reviewer")
        self.fill_review()
        report = build_report(self.output, root=self.root, ignore_check=lambda path, root: True)
        self.assertEqual(report["counts"], {
            "images": 2, "detections": 2, "true_positives": 1, "false_positives": 1, "false_negatives": 2, "images_without_detections": 1,
        })
        self.assertEqual(report["images_without_detections"], ["images/test/b.png"])
        self.assertEqual(report["false_negatives"], [{"image": "images/test/b.png", "missed_logos": 2}])
        markdown = (self.output / "report.md").read_text(encoding="utf-8")
        self.assertNotIn("%", markdown)
        self.assertIn("chosen by the reviewer", markdown)
        self.assertIn("not a blind independent test", markdown)
        self.assertEqual(json.loads((self.output / "report.json").read_text(encoding="utf-8"))["counts"], report["counts"])
        with self.assertRaises(FileExistsError):
            build_report(self.output, root=self.root, ignore_check=lambda path, root: True)


if __name__ == "__main__":
    unittest.main()
