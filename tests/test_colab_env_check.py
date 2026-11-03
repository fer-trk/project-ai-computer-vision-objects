"""Check that the Colab environment notebook stays a harmless, data-free check."""

import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "nox_colab_env_check.ipynb"
FORBIDDEN = (
    ".train(", ".predict(", "files.upload", "drive.mount", "ONE_RUN", "yolo11n", ".pt\"", "zipfile",
    "PERMISSIONS_CONFIRMED", "data/review", "data-synthetic",
)


class ColabEnvironmentNotebookTests(unittest.TestCase):
    def setUp(self):
        self.notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        self.code = [cell for cell in self.notebook["cells"] if cell["cell_type"] == "code"]

    def test_code_cells_parse_and_have_no_saved_outputs(self):
        self.assertEqual(len(self.code), 3)
        for cell in self.code:
            ast.parse("".join(cell["source"]))
            self.assertEqual(cell["outputs"], [])
            self.assertIsNone(cell["execution_count"])
        ids = [cell["id"] for cell in self.notebook["cells"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_notebook_cannot_train_upload_or_touch_project_data(self):
        text = "\n".join("".join(cell["source"]) for cell in self.code)
        for forbidden in FORBIDDEN:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_ultralytics_pin_matches_the_project_requirements(self):
        requirements = (ROOT / "requirements-inference.txt").read_text(encoding="utf-8").splitlines()
        pinned = next(line for line in requirements if line.startswith("ultralytics=="))
        text = "\n".join("".join(cell["source"]) for cell in self.code)
        self.assertIn(f'"{pinned}"', text)
        self.assertIn(f'== "{pinned.split("==")[1]}"', text)

    def test_gpu_is_required_and_declared(self):
        self.assertEqual(self.notebook["metadata"]["accelerator"], "GPU")
        self.assertIn("torch.cuda.is_available()", "".join(self.code[0]["source"]))


if __name__ == "__main__":
    unittest.main()
