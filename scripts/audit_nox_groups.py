"""Audit reviewed-image provenance and propose conservative source-group locks."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import cv2
import numpy as np


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def perceptual_hash(gray):
    """Return a 63-bit DCT hash for candidate discovery, not scene identity."""
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    coefficients = cv2.dct(resized.astype(np.float32))[:8, :8].flatten()[1:]
    bits = coefficients > np.median(coefficients)
    result = 0
    for bit in bits:
        result = (result << 1) | int(bit)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    root = args.project_root.resolve()
    output_root = args.output_root or root / "docs"
    output_root.mkdir(parents=True, exist_ok=True)
    inventory_path = root / "docs/nox-review-inventory-2026-10-26.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    event_tags = {"GermanyPremierPadelP2": "germany-p2", "OyshoMilanoPremierPadelP1": "milano-p1"}
    videos = {}
    for video_id in sorted({item["video_id"] for item in inventory["images"]}):
        metadata_path = root / "data/raw/videos" / f"{video_id}.info.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["id"] == video_id
        description = metadata.get("description", "")
        matches = [(tag, group) for tag, group in event_tags.items() if "#" + tag in description]
        assert len(matches) == 1, f"Ambiguous or missing origin tag: {video_id}"
        tag, group = matches[0]
        videos[video_id] = {
            "group_id": group, "observed_hashtag": "#" + tag,
            "metadata_path": metadata_path.relative_to(root).as_posix(),
            "metadata_sha256": sha256(metadata_path),
            "source_url": metadata.get("webpage_url"),
            "publication_date_metadata": metadata.get("upload_date"),
            "group_basis": "Observed event hashtag in local download metadata; publication date is not the match date.",
        }
    seen_hashes, rows = set(), []
    image_hashes = {}
    for image in inventory["images"]:
        path = (root / image["source_image"]).resolve()
        assert path.is_relative_to((root / "data/review").resolve())
        assert sha256(path) == image["image_sha256"]
        assert image["image_sha256"] not in seen_hashes
        seen_hashes.add(image["image_sha256"])
        gray = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert gray is not None and gray.shape == (1920, 1080)
        image_hashes[image["image_sha256"]] = perceptual_hash(gray)
        rows.append({
            "image_sha256": image["image_sha256"], "video_id": image["video_id"],
            "source_image": image["source_image"], "review_status": image["review_status"],
            "group_id": videos[image["video_id"]]["group_id"], "split": None,
        })
    candidates = []
    cross_video_compared = 0
    for first, second in combinations(rows, 2):
        if first["video_id"] == second["video_id"]:
            continue
        cross_video_compared += 1
        distance = (image_hashes[first["image_sha256"]] ^ image_hashes[second["image_sha256"]]).bit_count()
        if distance <= 8:
            candidates.append({"first": first["source_image"], "second": second["source_image"], "dct_hamming_distance": distance, "same_proposed_group": first["group_id"] == second["group_id"], "status": "candidate_not_confirmed_duplicate"})
    groups = []
    for group_id in sorted(set(event_tags.values())):
        selected = [row for row in rows if row["group_id"] == group_id]
        groups.append({"group_id": group_id, "video_ids": [video for video, info in videos.items() if info["group_id"] == group_id], "image_count": len(selected), "review_status_counts": dict(Counter(row["review_status"] for row in selected)), "split_lock": "Keep all images of this provisional event group together; no split assigned."})
    report = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Provenance audit of all 40 unique reviewed images; no labels or source media modified.",
        "inventory_path": inventory_path.relative_to(root).as_posix(), "inventory_sha256": sha256(inventory_path),
        "hash_checks_passed": len(rows), "image_dimensions_checked": len(rows),
        "exact_duplicates_in_unique_inventory": 0,
        "grouping_status": "provisional_conservative_event_locks_not_verified_match_identity",
        "groups": groups, "videos": videos, "images": rows,
        "similarity_scan": {"algorithm": "63-bit whole-frame grayscale DCT hash", "threshold_max_hamming": 8, "cross_video_pairs_compared": cross_video_compared, "candidates": sorted(candidates, key=lambda pair: pair["dct_hamming_distance"]), "limits": "A small distance flags visual similarity, not proven reuse. A larger distance does not establish independence, detect all crops or guarantee absence of repeated shots."},
        "training_validation_test_split_created": False,
        "decision": "Treat the two metadata-based event groups as indivisible for a conservative first experiment. Two groups cannot populate three disjoint nonempty group-level train/validation/test partitions. Any two-way exploratory experiment must retain the missing independent test as an explicit limitation.",
        "limits": ["Metadata hashtags are provenance hints and do not prove match identity or rule out reused edits.", "Publication dates are not event dates.", "Pending or excluded images stay pending or excluded; the audit does not approve them for training.", "Manual labeling quality, permissions and model quality are outside this scoped audit."],
    }
    destination = output_root / "nox-source-groups-2026-10-26.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checked": len(rows), "groups": groups, "cross_video_pairs_compared": cross_video_compared, "similarity_candidates": len(candidates), "cross_group_similarity_candidates": sum(not pair["same_proposed_group"] for pair in candidates), "output": str(destination)}))


if __name__ == "__main__":
    main()
