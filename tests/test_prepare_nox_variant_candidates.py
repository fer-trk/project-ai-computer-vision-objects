"""Check candidate selection avoids coarse similarity and temporal overlap."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_nox_variant_candidates import select_candidates


class CandidateSelectionTests(unittest.TestCase):
    def test_similar_frames_and_reviewed_reference_excluded(self):
        pool = [dict(video_id="a", frame_index=n, seconds=n * 2, fingerprint=value) for n, value in enumerate([0, 1, (1 << 20)-1, (1 << 20)-2])]
        selected = select_candidates(pool, [0])
        self.assertEqual(len(selected), 1)
        self.assertGreater(selected[0]["fingerprint"].bit_count(), 8)

    def test_temporal_spacing_and_per_video_cap(self):
        pool = [dict(video_id="a", frame_index=1, seconds=1, fingerprint=(1 << 20)-1), dict(video_id="a", frame_index=2, seconds=1.5, fingerprint=((1 << 20)-1) << 20), dict(video_id="b", frame_index=1, seconds=1, fingerprint=((1 << 20)-1) << 40)]
        selected = select_candidates(pool, [0], per_video=1)
        self.assertEqual([item["video_id"] for item in selected], ["a", "b"])
        self.assertEqual(len(select_candidates(pool, [0], per_video=10)), 2)


if __name__ == "__main__":
    unittest.main()
