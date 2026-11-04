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
from unittest.mock import patch

from PIL import Image
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_nox_text_run import (
    EvaluationError, ROOT, build_parser, build_report, git_ignores, run_evaluation,
)
from predict_image import PredictionError, file_hash
import evaluate_nox_text_run as evaluation

CLASSES = {0: "nox_texto"}


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name)
        self.root = self.tmp / "repo"
        self.dataset = self.tmp / "dataset"
        for index, (split, name) in enumerate((("test", "a.png"), ("test", "b.png"), ("train", "c.png"), ("val", "d.png"))):
            (self.dataset / "images" / split).mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (64, 48), (index * 40, 20, 10)).save(self.dataset / "images" / split / name)
        self.entries = [
            self.entry("test", "a.png", "hash-a", boxes=[[1, 1, 20, 20]]),
            self.entry("test", "b.png", "hash-b"),
            self.entry("train", "c.png", "hash-c"),
            self.entry("val", "d.png", "hash-d"),
        ]
        for entry in self.entries:
            entry["source_sha256"] = file_hash(self.dataset / entry["image"])
        self.training_run = self.root / "local-artifacts/nox-text-20261104-010101"
        self.checkpoint = self.training_run / "train/weights/best.pt"
        self.checkpoint.parent.mkdir(parents=True)
        self.checkpoint.write_bytes(b"controlled-checkpoint-fixture-not-a-model")
        self.output = self.root / "local-artifacts" / "run"
        self.manifest = self.write_manifest()
        self.write_training_run()

    @staticmethod
    def entry(split, name, digest, boxes=()):
        return {"image": f"images/{split}/{name}", "split": split, "source_sha256": digest,
                "width": 64, "height": 48, "boxes": list(boxes), "video_id": f"video-{split}", "group_id": f"group-{split}"}

    def write_training_run(self):
        """Build a hash-consistent T05 handoff fixture, without a trained model."""
        root = self.training_run
        (root / "train/weights/last.pt").write_bytes(b"fixture-last")
        (root / "train/args.yaml").write_text(yaml.safe_dump(dict(model="yolo11n.pt", **evaluation.t05.AGREED_PARAMETERS)))
        (root / "train/results.csv").write_text("epoch\n1\n")
        (root / "environment.json").write_text("{}")
        (root / "requirements-resolved.txt").write_text("fixture\n")
        (root / "dataset-manifest.json").write_bytes(self.manifest.read_bytes())
        (root / "experiment.json").write_text(json.dumps({
            "status": "training_completed", "run_name": root.name, "model": "yolo11n.pt",
            "dataset_zip_sha256": evaluation.t05.EXPECTED_DATASET_ZIP_SHA256,
            "parameters": evaluation.t05.AGREED_PARAMETERS, "confidence_threshold": .25,
            "confidence_rationale": "chosen by the reviewer",
        }))
        inventory = {"run_name": root.name, "status": "training_completed", "missing_required": [], "error_log_present": False,
                     "files": {name: {"sha256": file_hash(root / name), "bytes": (root / name).stat().st_size}
                               for name in evaluation.t05.REQUIRED}}
        (root / "run-manifest.json").write_text(json.dumps(inventory))
        report = {key: True for key in ("complete", "args_match_agreed", "experiment_match_agreed", "dataset_matches_approved",
                                        "model_matches_agreed", "confidence_selection_recorded")}
        report.update(run_name=root.name, errors=[], checkpoints={
            name: {"valid": True} for name in ("train/weights/best.pt", "train/weights/last.pt")})
        (root / "verification.json").write_text(json.dumps(report))
        patcher = patch.object(evaluation.t05, "EXPECTED_DATASET_MANIFEST_SHA256", file_hash(root / "dataset-manifest.json"))
        patcher.start()
        self.addCleanup(patcher.stop)

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
            confidence_rationale="chosen by the reviewer",
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
        for entries in (self.entries[2:], self.entries[:2] + [dict(self.entries[2], source_sha256=self.entries[0]["source_sha256"])]):
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
            "ambiguous_detections": 0, "ambiguous_logos": 0,
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

    def test_replaced_image_with_same_dimensions_blocks_all_predictions(self):
        Image.new("RGB", (64, 48), "blue").save(self.dataset / "images/test/b.png")
        calls = []
        with self.assertRaisesRegex(EvaluationError, "hash real"):
            self.evaluate(predictor=self.predictor(calls))
        self.assertEqual(calls, [])
        self.assertFalse((self.training_run / "T10_STARTED.lock").exists())

    def test_shared_video_or_group_and_missing_provenance_are_blocked(self):
        for field in ("video_id", "group_id"):
            for value in (self.entries[2][field], ""):
                entries = [dict(self.entries[0], **{field: value})] + self.entries[1:]
                calls = []
                with self.subTest(field=field, value=value), self.assertRaisesRegex(EvaluationError, field):
                    self.evaluate(manifest=self.write_manifest(entries), predictor=self.predictor(calls))
                self.assertEqual(calls, [])

    def test_synthetic_manifest_is_blocked_outside_synthetic_folder(self):
        data = json.loads(self.manifest.read_text())
        data["synthetic"] = True
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(EvaluationError, "sintéticos"):
            self.evaluate()

    def test_missing_or_rejected_training_verification_blocks_before_prediction(self):
        path = self.training_run / "verification.json"
        original = path.read_bytes()
        path.unlink()
        calls = []
        with self.assertRaisesRegex(EvaluationError, "verification.json"):
            self.evaluate(predictor=self.predictor(calls))
        data = json.loads(original)
        data["complete"] = False
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(EvaluationError, "verificación"):
            self.evaluate(predictor=self.predictor(calls))
        self.assertEqual(calls, [])

    def test_changed_training_artifact_is_rejected(self):
        self.checkpoint.write_bytes(b"changed-checkpoint")
        calls = []
        with self.assertRaisesRegex(EvaluationError, "artefacto de T05 ha cambiado"):
            self.evaluate(predictor=self.predictor(calls))
        self.assertEqual(calls, [])

    def test_threshold_or_rationale_cannot_change_after_training(self):
        for options in ({"confidence": .9}, {"confidence_rationale": "chosen after seeing test"}, {"confidence_rationale": ""}):
            calls = []
            with self.subTest(options=options), self.assertRaises(EvaluationError):
                self.evaluate(**options, predictor=self.predictor(calls))
            self.assertEqual(calls, [])
        self.assertFalse((self.training_run / "T10_STARTED.lock").exists())

    def test_other_annotations_cannot_replace_the_verified_manifest(self):
        entries = [dict(self.entries[0], boxes=[])] + self.entries[1:]
        calls = []
        with self.assertRaisesRegex(EvaluationError, "no corresponde al dataset"):
            self.evaluate(manifest=self.write_manifest(entries), predictor=self.predictor(calls))
        self.assertEqual(calls, [])

    def test_documentary_fields_can_differ_without_changing_data_identity(self):
        data = json.loads(self.manifest.read_text())
        data["loader_validation"] = {"documentary": True}
        for entry in data["images"]:
            entry["source"] = "documentary source path, not an evaluation input"
        self.manifest.write_text(json.dumps(data))
        self.assertTrue(self.evaluate()["complete"])

    def test_exploratory_partition_cannot_be_relabelled_as_blind_test(self):
        data = json.loads(self.manifest.read_text())
        data["independent_blind_test"] = True
        self.manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(EvaluationError, "independencia"):
            self.evaluate()

    def test_second_output_does_not_authorize_another_evaluation(self):
        calls = []
        self.evaluate(predictor=self.predictor(calls))
        with self.assertRaisesRegex(EvaluationError, "ya se intentó"):
            self.evaluate(output=self.root / "local-artifacts/second", predictor=self.predictor(calls))
        self.assertEqual(len(calls), 2)

    def test_failed_prediction_consumes_the_single_attempt(self):
        def broken(*args, **options):
            raise RuntimeError("controlled inference failure")
        with self.assertRaisesRegex(RuntimeError, "controlled"):
            self.evaluate(predictor=broken)
        self.assertFalse(self.output.exists())
        self.assertEqual(json.loads((self.training_run / "T10_STARTED.lock").read_text())["status"], "failed")
        with self.assertRaisesRegex(EvaluationError, "ya se intentó"):
            self.evaluate()

    def test_ambiguous_cases_need_notes_and_stay_outside_tp_fp_fn(self):
        self.evaluate()
        self.fill_review()
        path = self.output / "review.json"
        review = json.loads(path.read_text())
        review["images"][0]["detections"][0]["verdict"] = "ambiguous"
        review["images"][1]["ambiguous_logos"] = 3
        path.write_text(json.dumps(review))
        with self.assertRaisesRegex(EvaluationError, "notas"):
            build_report(self.output, root=self.root, ignore_check=lambda path, root: True)
        review["images"][0]["notes"] = "logo partly occluded"
        path.write_text(json.dumps(review))
        report = build_report(self.output, root=self.root, ignore_check=lambda path, root: True)
        self.assertEqual(report["counts"]["true_positives"], 0)
        self.assertEqual(report["counts"]["false_positives"], 1)
        self.assertEqual(report["counts"]["false_negatives"], 2)
        self.assertEqual(report["counts"]["ambiguous_detections"], 1)
        self.assertEqual(report["counts"]["ambiguous_logos"], 3)

    def test_changed_prediction_artifact_cannot_be_reported_as_original_output(self):
        run = self.evaluate()
        self.fill_review()
        path = self.output / run["images"][0]["predictions_json"]
        path.write_text("{}")
        with self.assertRaisesRegex(EvaluationError, "artefacto de evaluación cambió"):
            build_report(self.output, root=self.root, ignore_check=lambda path, root: True)
        self.assertFalse((self.output / "report.json").exists())


if __name__ == "__main__":
    unittest.main()
