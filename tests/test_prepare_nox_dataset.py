"""Check box conversion and dataset integrity safeguards."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_nox_dataset as dataset


class DatasetTests(unittest.TestCase):
    def test_non_square_coordinates(self):
        self.assertEqual(dataset.normalized_box([20, 10, 60, 30], 100, 50), [0.4, 0.4, 0.4, 0.4])

    def test_invalid_boxes(self):
        for box in ([0, 0, 101, 20], [20, 0, 10, 20], [0, 0, float("nan"), 10], [0, 0, 0, 10]):
            with self.subTest(box=box), self.assertRaises(ValueError):
                dataset.normalized_box(box, 100, 50)

    def make_fixture(self, root):
        images, groups, annotations = [], [], {}
        for index, (group, positive) in enumerate((("milano-p1", True), ("germany-p2", False))):
            source = root / f"data/review/source{index}.png"
            source.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (100, 50), (index * 100, 0, 0)).save(source)
            image_hash = dataset.digest(source)
            status = "positive_without_recorded_ambiguity" if positive else "reviewed_negative"
            images.append(dict(image_sha256=image_hash, video_id=str(index), source_image=source.relative_to(root).as_posix(), review_status=status, ambiguous_region=False, clear_box_count=int(positive)))
            groups.append(dict(image_sha256=image_hash, video_id=str(index), review_status=status, group_id=group))
            annotations[image_hash] = dict(source="fixture", boxes=[dict(label="nox", visibility="clear", bbox_xyxy=[20, 10, 60, 30])] if positive else [])
        for filename in (dataset.INVENTORY, dataset.GROUPS, dataset.PILOT, dataset.EXPANSION, dataset.EXPANSION_MANIFEST, *dataset.USER_REVIEWS):
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        (root / dataset.INVENTORY).write_text(json.dumps(dict(images=images)), encoding="utf-8")
        (root / dataset.GROUPS).write_text(json.dumps(dict(inventory_sha256=dataset.digest(root / dataset.INVENTORY), images=groups)), encoding="utf-8")
        return annotations

    def test_build_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            annotations = self.make_fixture(root)
            output = root / "data/review/output"
            with patch.object(dataset, "annotation_sources", return_value=annotations):
                result = dataset.build_dataset(root, output)
                self.assertEqual(result["summary"]["train"]["boxes"], 1)
                self.assertEqual(result["summary"]["val"]["negative_images"], 1)
                self.assertEqual(next((output / "labels/val").glob("*.txt")).read_text(), "")
                with self.assertRaises(FileExistsError):
                    dataset.build_dataset(root, output)

    def test_corrupted_image_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            annotations = self.make_fixture(root)
            (root / "data/review/source0.png").write_bytes(b"corrupt")
            output = root / "data/review/output"
            with patch.object(dataset, "annotation_sources", return_value=annotations), self.assertRaises(ValueError):
                dataset.build_dataset(root, output)
            self.assertFalse(output.exists())

    def test_stale_inventory_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_fixture(root)
            with (root / dataset.INVENTORY).open("a", encoding="utf-8") as handle:
                handle.write("\n")
            with self.assertRaisesRegex(ValueError, "stale inventory"):
                dataset.build_dataset(root, root / "data/review/output")


if __name__ == "__main__":
    unittest.main()
