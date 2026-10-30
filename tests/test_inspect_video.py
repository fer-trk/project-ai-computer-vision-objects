"""Exercise real decoders using small locally generated videos."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from inspect_video import VideoError, inspect_video, open_video


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class VideoInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.cfr = cls.root / "constant.mp4"
        cls.vfr = cls.root / "variable.mp4"
        cls.offset = cls.root / "offset.mp4"
        cls.make_video(cls.cfr)
        cls.make_video(cls.vfr, "select='not(eq(n,3)+eq(n,4))'", "-fps_mode", "vfr")
        cls.make_video(cls.offset, "setpts=PTS+2/TB", "-fps_mode", "passthrough")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def make_video(cls, target, filter_value=None, *options):
        command = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=10:duration=1"]
        if filter_value:
            command += ["-vf", filter_value]
        subprocess.run(command + [*options, "-c:v", "mpeg4", "-q:v", "2", str(target)], check=True, capture_output=True)

    def test_constant_rate_decodes_every_frame_with_source_times(self):
        report = inspect_video(self.cfr)
        self.assertTrue(report["complete"])
        self.assertEqual(report["frames_decoded"], 10)
        self.assertEqual((report["width"], report["height"]), (64, 48))
        self.assertAlmostEqual(report["duration_seconds"], 1)
        self.assertAlmostEqual(report["last_timestamp_seconds"], 0.9)
        with open_video(self.cfr) as (_, frames):
            frame = next(frames)
            self.assertEqual(frame.image.shape, (48, 64, 3))

    def test_variable_rate_preserves_a_real_gap(self):
        with open_video(self.vfr) as (_, frames):
            timestamps = [frame.timestamp_seconds for frame in frames]
        self.assertEqual(len(timestamps), 8)
        self.assertEqual([round(t, 1) for t in timestamps], [0, .1, .2, .5, .6, .7, .8, .9])
        report = inspect_video(self.vfr)
        self.assertAlmostEqual(report["minimum_frame_step_seconds"], .1)
        self.assertAlmostEqual(report["maximum_frame_step_seconds"], .3)

    def test_nonzero_start_keeps_source_pts_and_normalizes_timeline(self):
        report = inspect_video(self.offset)
        self.assertAlmostEqual(report["first_source_pts_seconds"], 2)
        self.assertAlmostEqual(report["last_source_pts_seconds"], 2.9)
        self.assertAlmostEqual(report["last_timestamp_seconds"], .9)

    def test_missing_invalid_and_audio_only_files_are_rejected(self):
        invalid = self.root / "invalid.mp4"
        invalid.write_text("not a video", encoding="utf-8")
        audio = self.root / "audio.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=0.1", str(audio)], check=True, capture_output=True)
        for path in (self.root / "missing.mp4", invalid, audio):
            with self.subTest(path=path.name), self.assertRaises(VideoError):
                inspect_video(path)

    def test_explicit_duration_and_resolution_limits(self):
        for limits in ({"max_duration_seconds": .5}, {"max_pixels": 100}, {"max_duration_seconds": float("nan")}, {"max_pixels": -1}):
            with self.subTest(limits=limits), self.assertRaises(VideoError):
                inspect_video(self.cfr, **limits)

    def test_early_exit_closes_decoders_and_allows_reopening(self):
        for _ in range(3):
            with open_video(self.cfr) as (_, frames):
                self.assertEqual(next(frames).index, 0)
        self.assertEqual(inspect_video(self.cfr)["frames_decoded"], 10)

    def test_cli_failure_does_not_emit_a_success_report(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/inspect_video.py"), str(self.cfr), "--max-duration-seconds", "0.1"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Error de", result.stderr)

    def test_corrupted_stream_cannot_produce_a_complete_report(self):
        corrupt = self.root / "corrupted.mp4"
        content = bytearray(self.cfr.read_bytes())
        start = content.index(b"mdat") + 4
        content[start:start + 300] = b"\x00" * 300
        corrupt.write_bytes(content)
        with self.assertRaises(VideoError):
            inspect_video(corrupt)


if __name__ == "__main__":
    unittest.main()
