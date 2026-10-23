"""Validate delegated visual decisions and render a local annotation review pack."""

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--review", type=Path, default=Path("docs/nox-expansion-review-2026-10-23.json"))
    parser.add_argument("--output", type=Path, default=Path("data/review/nox-expansion-reviewed-2026-10-23"))
    args = parser.parse_args()
    project = args.project_root.resolve()
    review = json.loads((project / args.review).read_text(encoding="utf-8"))
    source_manifest = json.loads((project / review["source_manifest"]).read_text(encoding="utf-8"))
    source_root = (project / review["source_manifest"]).parent
    sources = {item["id"]: item for item in source_manifest["examples"]}
    assert len(sources) == len(review["examples"]) == 12
    assert {item["id"] for item in review["examples"]} == set(sources)
    output = (project / args.output).resolve()
    assert output.is_relative_to((project / "data/review").resolve())
    assert not output.exists(), "Refusing to overwrite an existing review pack"
    checked = []
    for item in review["examples"]:
        source = sources[item["id"]]
        path = (source_root / source["image"]).resolve()
        assert path.is_relative_to(source_root.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["image_sha256"]
        with Image.open(path) as image:
            width, height = image.size
        assert [width, height] == source["dimensions"]
        assert item["decision"] in {"clear_positive", "reviewed_negative", "exclude_ambiguous"}
        assert bool(item["boxes"]) == (item["decision"] == "clear_positive")
        for box in item["boxes"]:
            x1, y1, x2, y2 = box["bbox_xyxy"]
            assert all(type(v) is int for v in box["bbox_xyxy"])
            assert 0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height
            assert (box["label"], box["visibility"], box["support"]) == ("nox", "clear", "clothing")
        checked.append((item, source, path))
    (output / "previews").mkdir(parents=True)
    xml_root = ET.Element("annotations")
    ET.SubElement(xml_root, "version").text = "1.1"
    lines = ["# Revisión de ampliación NOX", "", "Revisión visual delegada de 12 originales. Paquete local para revisión, sin particiones ni entrenamiento. No se ha cargado en CVAT. Las regiones ambiguas se excluyen de la exportación; no equivalen a negativos.", "", "| ID | Decisión | Evidencia |", "| --- | --- | --- |"]
    with zipfile.ZipFile(output / "review-images.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        exported_id = 0
        for item, source, path in checked:
            if item["decision"] == "exclude_ambiguous":
                lines.append(f"| {item['id']} | Excluido: ambiguo | {item['reason']} |")
                continue
            archive.write(path, arcname=path.name)
            image_node = ET.SubElement(xml_root, "image", id=str(exported_id), name=path.name, width=str(source["dimensions"][0]), height=str(source["dimensions"][1]))
            exported_id += 1
            with Image.open(path) as image:
                preview = image.copy()
            draw = ImageDraw.Draw(preview)
            for box in item["boxes"]:
                x1, y1, x2, y2 = box["bbox_xyxy"]
                draw.rectangle((x1, y1, x2 - 1, y2 - 1), outline="#00ff66", width=3)
                draw.text((x1, max(0, y1 - 18)), "NOX / clear / clothing", fill="#00ff66")
                node = ET.SubElement(image_node, "box", label="nox", occluded="0", source="manual", z_order="0", xtl=str(x1), ytl=str(y1), xbr=str(x2), ybr=str(y2))
                ET.SubElement(node, "attribute", name="visibility").text = "clear"
                ET.SubElement(node, "attribute", name="support").text = "clothing"
            preview.save(output / "previews" / path.name)
            lines.append(f"| {item['id']} | {item['decision']} | [Vista](previews/{path.name}) |")
    ET.indent(xml_root)
    ET.ElementTree(xml_root).write(output / "annotations.xml", encoding="utf-8", xml_declaration=True)
    assert len(ET.parse(output / "annotations.xml").getroot().findall("image")) == exported_id
    with zipfile.ZipFile(output / "review-images.zip") as archive:
        assert archive.testzip() is None and len(archive.namelist()) == exported_id
        for item, source, path in checked:
            if item["decision"] != "exclude_ambiguous":
                assert hashlib.sha256(archive.read(path.name)).hexdigest() == source["image_sha256"]
    summary = dict(Counter(item["decision"] for item in review["examples"]))
    summary.update({"exported_images": exported_id, "exported_boxes": sum(len(item["boxes"]) for item in review["examples"]), "validation": "passed", "training_ready": False, "cvat_import_tested": False, "review_sha256": hashlib.sha256((project / args.review).read_bytes()).hexdigest()})
    (output / "verification.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
