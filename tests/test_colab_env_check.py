"""Check that the Colab environment notebook stays a harmless, data-free check."""

import ast
import contextlib
import importlib.metadata
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

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


class EnvironmentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        standalone = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
        training = json.loads((ROOT / "notebooks/nox_text_training.ipynb").read_text(encoding="utf-8"))
        def cells(notebook):
            return {cell["metadata"]["tags"][0]: "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"}
        self.standalone = cells(standalone)
        primary = cells(training)
        self.groups = (self.standalone, {"gpu-check": primary["gpu-check"], "install-check": primary["install"]})

    @staticmethod
    def torch(available=True, probe_ok=True):
        class Tensor:
            def __matmul__(self, other):
                return self
            def __getitem__(self, index):
                return self
            def item(self):
                return 16 if probe_ok else 0
        return types.SimpleNamespace(
            cuda=types.SimpleNamespace(is_available=available if callable(available) else lambda: available,
                                       get_device_name=lambda index: "fixture GPU", empty_cache=lambda: None),
            ones=lambda *args, **kwargs: Tensor(), version=types.SimpleNamespace(cuda="fixture"), __version__="fixture",
        )

    def execute(self, source, state, torch, commands, *, bad_check=False, version="8.4.189"):
        """Run cells with package installation, CUDA and model construction replaced."""
        module = types.ModuleType("ultralytics")
        module.settings = {key: True for key in ("sync", "wandb", "mlflow", "comet", "clearml")}
        module.YOLO = lambda *args, **kwargs: self.fail("Preflight must not construct a model")
        def command(args, **options):
            commands.append(args)
            if bad_check and args[-1] == "check":
                raise subprocess.CalledProcessError(1, args)
            return types.SimpleNamespace(stdout="fixture==1\n", returncode=0)
        state.update(torch=torch, sys=sys, subprocess=subprocess, environment=state.get("environment", {}))
        source = source.replace('Path("/content/nox-text-work")', f"Path({str(self.root / 'work')!r})")
        with patch.dict(sys.modules, {"torch": torch, "ultralytics": module}), \
                patch("subprocess.run", side_effect=command), \
                patch("importlib.util.find_spec", return_value=None), \
                patch("importlib.metadata.version", return_value=version), contextlib.redirect_stdout(io.StringIO()):
            exec(source, state)
        return module.settings

    def test_no_gpu_clears_stale_success_and_never_installs(self):
        for sources in self.groups:
            state = {"GPU_CHECK_PASSED": True, "ENVIRONMENT_READY": True}
            calls = []
            with self.assertRaisesRegex(RuntimeError, "GPU CUDA"):
                self.execute(sources["gpu-check"], state, self.torch(False), calls)
            self.assertFalse(state["GPU_CHECK_PASSED"])
            self.assertFalse(state["ENVIRONMENT_READY"])
            self.assertEqual(calls, [])

    def test_installation_cannot_skip_gpu_gate(self):
        for sources in self.groups:
            calls = []
            with self.assertRaisesRegex(RuntimeError, "GPU"):
                self.execute(sources["install-check"], {}, self.torch(), calls)
            self.assertEqual(calls, [])

    def test_broken_gpu_operation_never_marks_ready(self):
        for sources in self.groups:
            state = {}
            with self.assertRaises(AssertionError):
                self.execute(sources["gpu-check"], state, self.torch(probe_ok=False), [])
            self.assertFalse(state["GPU_CHECK_PASSED"])
            self.assertFalse(state["ENVIRONMENT_READY"])

    def test_successful_checks_require_no_real_installation_or_model(self):
        for sources in self.groups:
            state, calls, torch = {}, [], self.torch()
            self.execute(sources["gpu-check"], state, torch, calls)
            settings = self.execute(sources["install-check"], state, torch, calls)
            self.assertTrue(state["ENVIRONMENT_READY"])
            self.assertTrue(all(value is False for value in settings.values()))
            self.assertTrue(any(args[-1] == "check" for args in calls))
            if "summary" in sources:
                self.execute(sources["summary"], state, torch, calls)

    def test_dependency_check_failure_blocks_readiness(self):
        for sources in self.groups:
            state, calls, torch = {}, [], self.torch()
            self.execute(sources["gpu-check"], state, torch, calls)
            with self.assertRaises(subprocess.CalledProcessError):
                self.execute(sources["install-check"], state, torch, calls, bad_check=True)
            self.assertFalse(state["ENVIRONMENT_READY"])

    def test_gpu_loss_during_installation_blocks_readiness(self):
        for sources in self.groups:
            available = iter((True, True, False))
            torch = self.torch(lambda: next(available))
            state, calls = {}, []
            self.execute(sources["gpu-check"], state, torch, calls)
            with self.assertRaisesRegex(RuntimeError, "GPU"):
                self.execute(sources["install-check"], state, torch, calls)
            self.assertFalse(state["ENVIRONMENT_READY"])

    def test_wrong_library_version_blocks_readiness(self):
        for sources in self.groups:
            state, calls, torch = {}, [], self.torch()
            self.execute(sources["gpu-check"], state, torch, calls)
            with self.assertRaises((RuntimeError, AssertionError)):
                self.execute(sources["install-check"], state, torch, calls, version="different")
            self.assertFalse(state["ENVIRONMENT_READY"])

    def test_summary_cannot_announce_success_after_failure(self):
        with self.assertRaisesRegex(RuntimeError, "no está listo"):
            self.execute(self.standalone["summary"], {}, self.torch(), [])


if __name__ == "__main__":
    unittest.main()
