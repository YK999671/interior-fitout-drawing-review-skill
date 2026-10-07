#!/usr/bin/env python3
"""Read DWG through an installed ODA File Converter and extract DXF entities.

Source drawings are never changed. Converted DXF and JSON are written under
the output directory. ODA File Converter is an external application and is
not distributed with this skill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import ezdxf
    from ezdxf.addons import odafc
except ImportError as exc:
    raise SystemExit("CAD parsing requires ezdxf: python -m pip install -r requirements-cad.txt") from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def oda_path(explicit: str | None) -> Path | None:
    if explicit:
        selected = Path(explicit)
        return selected.resolve() if selected.is_file() else None
    choices = [explicit, os.environ.get("ODA_FILE_CONVERTER"), shutil.which("ODAFileConverter")]
    if os.name == "nt":
        for parent in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ODA",
                       Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "ODA"):
            if parent.is_dir():
                choices.extend(str(p) for p in sorted(parent.glob("*/ODAFileConverter.exe"), reverse=True))
    for item in choices:
        if item and Path(item).is_file():
            return Path(item).resolve()
    return None


def point(value):
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def dxf_value(entity, name):
    try:
        return entity.dxf.get(name)
    except (AttributeError, ValueError):
        return None


def describe(entity, container: str, coordinate_space: str) -> dict:
    kind = entity.dxftype()
    row = {
        "type": kind,
        "handle": dxf_value(entity, "handle"),
        "layer": dxf_value(entity, "layer"),
        "container": container,
        "coordinate_space": coordinate_space,
    }
    if kind in {"TEXT", "ATTRIB", "ATTDEF"}:
        row.update(text=dxf_value(entity, "text"), insert=point(dxf_value(entity, "insert")),
                   height=dxf_value(entity, "height"), rotation=dxf_value(entity, "rotation"),
                   style=dxf_value(entity, "style"))
        if kind != "TEXT":
            row["tag"] = dxf_value(entity, "tag")
    elif kind == "MTEXT":
        row.update(text=entity.plain_text(), raw_text=dxf_value(entity, "text"),
                   insert=point(dxf_value(entity, "insert")), char_height=dxf_value(entity, "char_height"),
                   style=dxf_value(entity, "style"))
    elif kind == "DIMENSION":
        row.update(text=dxf_value(entity, "text"), dimstyle=dxf_value(entity, "dimstyle"),
                   dimtype=dxf_value(entity, "dimtype"), defpoint=point(dxf_value(entity, "defpoint")),
                   text_midpoint=point(dxf_value(entity, "text_midpoint")))
        try:
            measurement = entity.get_measurement()
            row["measurement_drawing_units"] = float(measurement) if isinstance(measurement, (int, float)) else point(measurement)
        except Exception as exc:
            row["measurement_error"] = type(exc).__name__
    elif kind == "INSERT":
        row.update(block_name=dxf_value(entity, "name"), insert=point(dxf_value(entity, "insert")),
                   xscale=dxf_value(entity, "xscale"), yscale=dxf_value(entity, "yscale"),
                   zscale=dxf_value(entity, "zscale"), rotation=dxf_value(entity, "rotation"),
                   attributes=[{"tag": dxf_value(a, "tag"), "text": dxf_value(a, "text"),
                                "insert": point(dxf_value(a, "insert"))} for a in entity.attribs])
    elif kind == "LINE":
        row.update(start=point(dxf_value(entity, "start")), end=point(dxf_value(entity, "end")))
    elif kind == "LWPOLYLINE":
        row.update(vertices=[[float(x), float(y)] for x, y in entity.get_points("xy")],
                   closed=entity.closed)
    elif kind == "POLYLINE":
        row.update(vertices=[point(v.dxf.location) for v in entity.vertices], closed=entity.is_closed)
    elif kind in {"CIRCLE", "ARC"}:
        row.update(center=point(dxf_value(entity, "center")), radius=dxf_value(entity, "radius"))
        if kind == "ARC":
            row.update(start_angle=dxf_value(entity, "start_angle"), end_angle=dxf_value(entity, "end_angle"))
    elif kind == "POINT":
        row["location"] = point(dxf_value(entity, "location"))
    elif kind == "HATCH":
        row.update(pattern_name=dxf_value(entity, "pattern_name"),
                   solid_fill=dxf_value(entity, "solid_fill"), boundary_paths=len(entity.paths))
    elif kind == "LEADER":
        row["vertices"] = [point(v) for v in entity.vertices]
    elif kind == "SPLINE":
        row.update(control_points=[point(v) for v in entity.control_points],
                   fit_points=[point(v) for v in entity.fit_points])
    elif kind == "MULTILEADER":
        try:
            row["text"] = entity.context.mtext.text
        except (AttributeError, TypeError):
            pass
    return row


def parse_document(doc, max_entities: int) -> dict:
    entities = []
    counts = Counter()
    layer_counts = Counter()
    warnings = []
    truncated = False
    layout_names = []

    def collect(container, space, drawing):
        nonlocal truncated
        for entity in drawing:
            kind = entity.dxftype()
            counts[kind] += 1
            layer_counts[str(dxf_value(entity, "layer") or "")] += 1
            if max_entities and len(entities) >= max_entities:
                truncated = True
                continue
            try:
                entities.append(describe(entity, container, space))
            except Exception as exc:
                entities.append({"type": kind, "handle": dxf_value(entity, "handle"),
                                 "container": container, "parse_error": type(exc).__name__})
                warnings.append(f"{container}:{kind}:{type(exc).__name__}")

    for layout in doc.layouts:
        layout_names.append(layout.name)
        collect(f"layout:{layout.name}", "layout", layout)
    block_names = []
    xrefs = []
    for block in doc.blocks:
        name = block.name
        if name.startswith(("*Model_Space", "*Paper_Space")):
            continue
        block_names.append(name)
        flags = int(dxf_value(block.block, "flags") or 0)
        if flags & (4 | 8):
            xrefs.append({"name": name, "path": dxf_value(block.block, "xref_path"),
                          "status": "not_resolved_by_this_parser"})
        collect(f"block:{name}", "block_local", block)
    if xrefs:
        warnings.append("External references are listed but not resolved or positioned.")
    if counts["ACAD_PROXY_ENTITY"] or counts["ACAD_PROXY_OBJECT"]:
        warnings.append("Proxy objects require a CAD application or the originating plug-in for verification.")
    if counts["INSERT"]:
        warnings.append("Block definitions use local coordinates; INSERT transforms are recorded but not expanded.")
    if truncated:
        warnings.append("Entity output reached --max-entities; counts include omitted entities.")
    layers = []
    for layer in doc.layers:
        layers.append({"name": layer.dxf.name, "color": layer.dxf.color,
                       "flags": layer.dxf.flags, "linetype": layer.dxf.linetype})
    return {
        "dxf_version": doc.dxfversion,
        "drawing_units_code": doc.header.get("$INSUNITS", 0),
        "layouts": layout_names,
        "layers": layers,
        "block_definitions": block_names,
        "xrefs": xrefs,
        "entity_count_by_type": dict(sorted(counts.items())),
        "entity_count_by_layer": dict(sorted(layer_counts.items())),
        "entities_exported": len(entities),
        "entities_truncated": truncated,
        "warnings": sorted(set(warnings)),
        "entities": entities,
    }


def files_to_parse(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix.lower() in {".dwg", ".dxf"} else []
    return sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in {".dwg", ".dxf"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="A DWG/DXF file or directory")
    parser.add_argument("-o", "--output", required=True, help="Separate directory for converted DXF and JSON")
    parser.add_argument("--oda-exe", help="Absolute path to the installed ODAFileConverter executable")
    parser.add_argument("--manifest", help="Optional manifest from inventory_files.py to annotate")
    parser.add_argument("--max-entities", type=int, default=250000,
                        help="Per-file JSON entity limit; 0 disables the limit (default: 250000)")
    args = parser.parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.exists():
        parser.error(f"Source does not exist: {source}")
    if args.max_entities < 0:
        parser.error("--max-entities must be nonnegative")
    if source.is_file() and output == source.parent:
        parser.error("Output must be separate from the source drawing directory")
    if source.is_dir() and (output == source or source in output.parents):
        parser.error("Output must be outside the source drawing tree")
    output.mkdir(parents=True, exist_ok=True)
    oda = oda_path(args.oda_exe)
    if args.oda_exe and oda is None:
        parser.error(f"ODA executable not found: {args.oda_exe}")
    if oda:
        ezdxf.options.set("odafc-addon", "win_exec_path" if os.name == "nt" else "unix_exec_path", str(oda))
    cad_files = files_to_parse(source)
    if not cad_files:
        print("No DWG or DXF files found", file=sys.stderr)
        return 2
    index = {"schema_version": "1.0", "source": str(source), "created_utc": datetime.now(timezone.utc).isoformat(),
             "oda_executable": str(oda) if oda else None, "ezdxf_version": ezdxf.__version__, "files": []}
    for path in cad_files:
        relative = path.name if source.is_file() else str(path.relative_to(source))
        digest_before = sha256(path)
        record = {"relative_path": relative, "source_sha256": digest_before, "format": path.suffix.lower(),
                  "parse_status": "not_attempted"}
        target_dir = output / hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12]
        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "drawing.json"
        try:
            if path.suffix.lower() == ".dwg":
                if oda is None:
                    record.update(parse_status="converter_unavailable", error="ODA File Converter is not installed")
                    record["source_unchanged"] = sha256(path) == digest_before
                    index["files"].append(record)
                    print(json.dumps({"file": relative, "status": record["parse_status"]}, ensure_ascii=False), flush=True)
                    continue
                converted = target_dir / "converted.dxf"
                if converted.exists():
                    converted.unlink()
                odafc.convert(path, converted, version="R2018", audit=False, replace=False)
                if not converted.is_file():
                    raise RuntimeError("ODA conversion returned without a DXF file")
                record["converted_dxf"] = str(converted)
                record["converted_sha256"] = sha256(converted)
                doc = ezdxf.readfile(converted)
            else:
                doc = ezdxf.readfile(path)
            parsed = parse_document(doc, args.max_entities)
            record["parse_status"] = "partial" if parsed["entities_truncated"] or parsed["xrefs"] or parsed["entity_count_by_type"].get("ACAD_PROXY_ENTITY") else "parsed"
            record["json"] = str(json_path)
            record["entity_count"] = sum(parsed["entity_count_by_type"].values())
            record["warnings"] = parsed["warnings"]
            json_path.write_text(json.dumps({"source": record, "drawing": parsed}, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except Exception as exc:
            record.update(parse_status="parse_failed", error=f"{type(exc).__name__}: {exc}")
        digest_after = sha256(path)
        record["source_unchanged"] = digest_before == digest_after
        if not record["source_unchanged"]:
            record["parse_status"] = "source_changed"
        index["files"].append(record)
        print(json.dumps({"file": relative, "status": record["parse_status"],
                          "entities": record.get("entity_count", 0)}, ensure_ascii=False), flush=True)
    index_path = output / "cad-parse-index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        by_path = {item["relative_path"]: item for item in index["files"]}
        for item in manifest.get("files", []):
            parsed = by_path.get(item["relative_path"])
            if parsed:
                item["parse_status"] = parsed["parse_status"]
                item["parse_result"] = parsed.get("json")
        (output / "manifest-with-cad-status.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"index": str(index_path), "files": len(index["files"]),
                      "parsed": sum(x["parse_status"] == "parsed" for x in index["files"]),
                      "partial": sum(x["parse_status"] == "partial" for x in index["files"]),
                      "failed_or_unavailable": sum(x["parse_status"] not in {"parsed", "partial"} for x in index["files"])},
                     ensure_ascii=False))
    return 0 if all(x["parse_status"] in {"parsed", "partial"} for x in index["files"]) else 2


if __name__ == "__main__":
    sys.exit(main())
