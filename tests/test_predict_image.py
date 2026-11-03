"""Check image rendering and exports independently of detector quality."""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from predict_image import PredictionError, file_hash, run_inference


class ImagePredictionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.image = self.root / "source.png"
        Image.new("RGB", (320, 240), "white").save(self.image)
        self.checkpoint = self.root / "fixture.pt"
        self.checkpoint.write_bytes(b"controlled-predictor-fixture-not-a-model")
        self.output = self.root / "result"

    def predict(self, detections):
        def controlled(checkpoint, image, **options):
            self.assertEqual(checkpoint, self.checkpoint)
            self.assertEqual(image.size, (320, 240))
            self.assertEqual(options["confidence"], .25)
            return {0: "nox_texto", 1: "nox_simbolo"}, detections
        return controlled

    def run_prediction(self, detections, **options):
        return run_inference(self.image, self.checkpoint, self.output, confidence=.25, predictor=self.predict(detections), **options)

    def test_detections_keep_box_class_score_and_checkpoint_identity(self):
        before = file_hash(self.image)
        detections = [
            {"bbox_xyxy": [10, 20, 60, 50], "class_id": 0, "confidence": .8},
            {"bbox_xyxy": [210, 170, 319, 239], "class_id": 1, "confidence": .4},
        ]
        report = self.run_prediction(detections)
        self.assertEqual(report["detection_count"], 2)
        self.assertEqual(report["model"]["sha256"], file_hash(self.checkpoint))
        self.assertEqual(file_hash(self.image), before)
        persisted = json.loads((self.output / "predictions.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["detections"], report["detections"])
        with (self.output / "predictions.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(rows[1]["class_name"], "nox_simbolo")
        self.assertEqual(float(rows[1]["x2"]), 319)
        self.assertEqual(rows[1]["evidence_status"], "unreviewed")
        with Image.open(self.output / "annotated.png") as rendered:
            self.assertEqual(rendered.size, (320, 310))
            self.assertEqual(rendered.getpixel((10, 58)), (255, 179, 71))
            self.assertNotEqual(rendered.getpixel((10, 93)), (255, 255, 255))

    def test_no_detections_writes_empty_list_csv_header_and_viewable_image(self):
        report = self.run_prediction([])
        self.assertEqual(report["detections"], [])
        with (self.output / "predictions.csv").open(encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 1)
        self.assertTrue((self.output / "annotated.png").is_file())

    def test_overlapping_edge_boxes_keep_all_labels_in_expanded_footer(self):
        detections = [{"bbox_xyxy": [220, 200, 320, 240], "class_id": 0, "confidence": .8} for _ in range(4)]
        report = self.run_prediction(detections)
        self.assertGreaterEqual(report["rendering"]["footer_pixels"], 98)
        with Image.open(self.output / "annotated.png") as rendered:
            self.assertEqual(rendered.getpixel((319, 238)), (255, 179, 71))
            for top in (280, 304, 328, 352):
                self.assertEqual(rendered.getpixel((20, top)), (23, 32, 43))

    def test_invalid_or_missing_image_never_publishes_results(self):
        self.image.write_text("not an image", encoding="utf-8")
        with self.assertRaises(PredictionError):
            self.run_prediction([])
        self.image.unlink()
        with self.assertRaises(PredictionError):
            self.run_prediction([])
        self.assertFalse(self.output.exists())

    def test_existing_results_are_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.run_prediction([])
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_invalid_boxes_classes_and_scores_are_rejected(self):
        for detection in (
            {"bbox_xyxy": [1, 2, 1, 5], "class_id": 0, "confidence": .4},
            {"bbox_xyxy": [-1, 0, 15, 25], "class_id": 0, "confidence": .4},
            {"bbox_xyxy": [0, 0, 321, 240], "class_id": 0, "confidence": .4},
            {"bbox_xyxy": [0, 0, float("nan"), 240], "class_id": 0, "confidence": .4},
            {"bbox_xyxy": [1, 2, 10, 20], "class_id": 3, "confidence": .4},
            {"bbox_xyxy": [1, 2, 10, 20], "class_id": .5, "confidence": .4},
            {"bbox_xyxy": [1, 2, 10, 20], "class_id": 0, "confidence": 1.1},
        ):
            with self.subTest(detection=detection), self.assertRaises(PredictionError):
                self.run_prediction([detection])
            self.assertFalse(self.output.exists())

    def test_invalid_options_and_missing_checkpoint_fail_before_prediction(self):
        for parameters in ({"confidence": float("nan")}, {"confidence": -1}, {"confidence": .25, "iou": 2}, {"confidence": .25, "image_size": 0}, {"confidence": .25, "image_size": 641}):
            with self.subTest(parameters=parameters), self.assertRaises(PredictionError):
                run_inference(self.image, self.checkpoint, self.output, **parameters)
        self.checkpoint.unlink()
        with self.assertRaises(PredictionError):
            self.run_prediction([])

    def test_exif_rotation_is_applied_to_both_prediction_and_report(self):
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (40, 20), "white").save(self.image, format="JPEG", exif=exif)
        def predictor(checkpoint, image, **options):
            self.assertEqual(image.size, (20, 40))
            return {0: "nox"}, []
        report = run_inference(self.image, self.checkpoint, self.output, confidence=.25, predictor=predictor)
        self.assertEqual((report["image"]["width"], report["image"]["height"]), (20, 40))

    def test_transparent_pixels_use_the_documented_white_background(self):
        Image.new("RGBA", (320, 240), (255, 0, 0, 0)).save(self.image)
        def predictor(checkpoint, image, **options):
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
            return {0: "nox"}, []
        run_inference(self.image, self.checkpoint, self.output, confidence=.25, predictor=predictor)

    def test_model_failure_and_write_failure_do_not_publish_partial_results(self):
        def failure(*args, **kwargs):
            raise RuntimeError("controlled failure")
        with self.assertRaises(RuntimeError):
            run_inference(self.image, self.checkpoint, self.output, confidence=.25, predictor=failure)
        with patch("predict_image.Image.Image.save", side_effect=OSError("disk full")), self.assertRaises(OSError):
            self.run_prediction([])
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".prediction-*")), [])


if __name__ == "__main__":
    unittest.main()
