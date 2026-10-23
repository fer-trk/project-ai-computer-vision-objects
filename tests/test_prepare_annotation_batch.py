"""Protect annotation review integrity and prevent silent training labels."""

import copy
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_annotation_batch import file_hash, prepare_batch


class AnnotationBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        run = self.root / "data/review/source"
        image_path = run / "frames/video1/T01.png"
        image_path.parent.mkdir(parents=True)
        Image.new("RGB", (64, 48), "red").save(image_path)
        video_path = self.root / "data/raw/videos/video1.mp4"
        video_path.parent.mkdir(parents=True)
        video_path.write_bytes(b"source video fixture")
        self.source_manifest = run / "manifest.json"
        self.manifest = {"videos": [{
            "video_id": "video1", "filename": "video1.mp4",
            "sha256": file_hash(video_path), "source_url": "https://example.org/video1",
            "samples": [{"image": "frames/video1/T01.png", "frame_index": 25,
                         "reference_seconds": 1.0, "width": 64, "height": 48,
                         "timestamp_basis": "decoder_pos_msec"}],
        }]}
        self.source_manifest.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.pilot = {"schema_version": 1, "first_brand": "NOX", "examples": [{
            "id": "N01", "video_id": "video1", "frame_index": 25,
            "timestamp_seconds": 1.0, "image": image_path.relative_to(self.root).as_posix(),
            "image_sha256": file_hash(image_path), "image_width": 64, "image_height": 48,
            "brand": "NOX", "support": "clothing", "placement": "chest",
            "evidence_category": 1, "proposed_bbox_xyxy": [10, 10, 20, 20],
            "bbox_status": "proposed_pending_user_review",
        }]}
        self.pilot_path = self.root / "docs/pilot.json"
        self.pilot_path.parent.mkdir()
        self.output = self.root / "data/review/output"

    def prepare(self, check_only=False):
        self.pilot_path.write_text(json.dumps(self.pilot), encoding="utf-8")
        return prepare_batch(self.root, self.pilot_path, self.output, check_only)

    def test_archive_preserves_pixels_and_keeps_boxes_pending(self):
        original_pilot = copy.deepcopy(self.pilot)
        records = self.prepare()
        with zipfile.ZipFile(self.output / "images.zip") as archive:
            self.assertEqual(archive.namelist(), ["N01_video1_f000025.png"])
            self.assertEqual(archive.read(archive.namelist()[0]), (self.root / self.pilot["examples"][0]["image"]).read_bytes())
        self.assertEqual(records[0]["annotation_status"], "pending_manual_review")
        self.assertIsNone(records[0]["split"])
        self.assertEqual(json.loads(self.pilot_path.read_text()), original_pilot)
        self.assertFalse((self.output / "labels").exists())

    def test_modified_image_is_rejected_before_output_is_created(self):
        (self.root / self.pilot["examples"][0]["image"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Image hash mismatch"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_duplicate_source_frame_is_rejected(self):
        second = copy.deepcopy(self.pilot["examples"][0])
        second["id"] = "N02"
        self.pilot["examples"].append(second)
        with self.assertRaisesRegex(ValueError, "Duplicate image or source frame"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_invalid_box_is_rejected(self):
        self.pilot["examples"][0]["proposed_bbox_xyxy"] = [10, 10, 80, 20]
        with self.assertRaisesRegex(ValueError, "Proposed box outside image"):
            self.prepare()

    def test_wrong_timestamp_is_rejected(self):
        self.pilot["examples"][0]["timestamp_seconds"] = 2.0
        with self.assertRaisesRegex(ValueError, "Extraction reference mismatch"):
            self.prepare()

    def test_modified_video_is_rejected(self):
        (self.root / "data/raw/videos/video1.mp4").write_bytes(b"different video")
        with self.assertRaisesRegex(ValueError, "Source video hash mismatch"):
            self.prepare()

    def test_check_only_creates_no_batch(self):
        self.assertEqual(len(self.prepare(check_only=True)), 1)
        self.assertFalse(self.output.exists())

    def test_existing_batch_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.prepare()
        self.assertEqual(sentinel.read_text(), "keep")

    def test_output_outside_ignored_review_directory_is_rejected(self):
        self.output = self.root / "public-dataset"
        with self.assertRaisesRegex(ValueError, "Path leaves"):
            self.prepare()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
