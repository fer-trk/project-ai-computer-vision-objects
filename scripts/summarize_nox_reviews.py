"""Count unique reviewed images without converting review data to training labels."""

import hashlib
import json
from collections import Counter
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
workspace = repo / "docs"
records = {}


def add(image_hash, video_id, path, source, clear_count=0, ambiguous=False, negative=False):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == image_hash
    source_path = path.relative_to(repo).as_posix() if path.is_relative_to(repo) else "data/review/" + path.relative_to(workspace/"local-artifacts").as_posix()
    entry = records.setdefault(image_hash, {"image_sha256":image_hash,"video_id":video_id,"source_image":source_path,"review_sources":[],"clear_box_count":0,"ambiguous_region":False,"reviewed_negative":False})
    assert entry["video_id"] == video_id
    entry["review_sources"].append(source)
    entry["clear_box_count"] = max(entry["clear_box_count"], clear_count)
    entry["ambiguous_region"] |= ambiguous
    entry["reviewed_negative"] |= negative


pilot_manifest = json.loads((repo / "data/review/nox-cvat-pilot-2026-10-21/manifest.json").read_text(encoding="utf-8"))
pilot_by_id = {item["id"]:item for item in pilot_manifest["examples"]}
pilot = json.loads((repo / "data/review/exports/nox-cvat-export-2026-10-23/verification.json").read_text(encoding="utf-8"))
for item in pilot["examples"]:
    source = pilot_by_id[item["id"]]
    clear = sum(box["attributes"]["visibility"] == "clear" for box in item["boxes"])
    add(item["image_sha256"],source["video_id"],repo/source["source_image"],"cvat_pilot_2026-10-23:"+item["id"],clear,any(box["attributes"]["visibility"]!="clear" for box in item["boxes"]))
expansion_manifest = json.loads((repo / "data/review/nox-expansion-2026-10-23/manifest.json").read_text(encoding="utf-8"))
expansion_sources = {item["id"]:item for item in expansion_manifest["examples"]}
review = json.loads((repo / "docs/nox-expansion-review-2026-10-23.json").read_text(encoding="utf-8"))
for item in review["examples"]:
    source = expansion_sources[item["id"]]
    add(source["image_sha256"],source["video_id"],repo/"data/review/nox-expansion-2026-10-23"/source["image"],"expansion_2026-10-23:"+item["id"],len(item["boxes"]),item["decision"]=="exclude_ambiguous",item["decision"]=="reviewed_negative")
for filename, local in [("review-user-moments-decisions-2026-10-26.json",False),("review-user-video2-decisions-2026-10-26.json",True)]:
    review = json.loads(((workspace if local else repo/"docs") / filename).read_text(encoding="utf-8"))
    for item in review["examples"]:
        path = repo/item["source_image"]
        if not path.exists():
            parts = Path(item["source_image"]).parts
            path = workspace/"local-artifacts"/Path(*parts[2:])
        add(item["image_sha256"],item["video_id"],path,filename+":"+str(item["reference_seconds"]),len(item["boxes"]),item["decision"]=="hold_for_review")
for entry in records.values():
    assert not (entry["reviewed_negative"] and entry["clear_box_count"])
    entry["review_status"] = "positive_without_recorded_ambiguity" if entry["clear_box_count"] and not entry["ambiguous_region"] else ("reviewed_negative" if entry["reviewed_negative"] else "held_or_excluded")
counts = Counter(entry["review_status"] for entry in records.values())
report = {
    "schema_version":1,"date_local":"2026-10-26","unique_reviewed_images":len(records),
    "images_with_clear_box":sum(entry["clear_box_count"]>0 for entry in records.values()),
    "review_status_counts":dict(counts),"video_count":len({entry["video_id"] for entry in records.values()}),
    "training_ready":False,"splits_created":False,
    "limits":"Review inventory only, not an approved training selection. Positive counts require no recorded ambiguous region in the same image. Clips may share shots or match origin; independent groups are not yet validated. Some held entries represent off-screen targets or non-target cuts rather than ambiguous NOX.",
    "images":sorted(records.values(),key=lambda item:(item["video_id"],item["image_sha256"])),
}
(workspace/"nox-review-inventory-2026-10-26.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({key:value for key,value in report.items() if key!="images"}))
