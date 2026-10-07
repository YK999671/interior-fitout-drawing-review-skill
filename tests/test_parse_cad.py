"""Synthetic DXF and optional ODA DWG round-trip; no project drawings."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import ezdxf
from ezdxf.addons import odafc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from parse_cad import oda_path  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(source, output):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "parse_cad.py"), str(source), "-o", str(output)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    index = json.loads((output / "cad-parse-index.json").read_text(encoding="utf-8"))
    assert len(index["files"]) == 1
    item = index["files"][0]
    assert item["parse_status"] == "parsed", item
    assert item["source_unchanged"] is True
    data = json.loads(Path(item["json"]).read_text(encoding="utf-8"))
    return data


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        doc = ezdxf.new("R2018")
        doc.layers.new("FINISH")
        model = doc.modelspace()
        model.add_text("CT-02", dxfattribs={"layer": "FINISH", "height": 100})
        model.add_mtext("墙面材料说明", dxfattribs={"layer": "FINISH"})
        model.add_line((0, 0), (1000, 0), dxfattribs={"layer": "FINISH"})
        block = doc.blocks.new("SINK")
        block.add_circle((0, 0), 200)
        model.add_blockref("SINK", (500, 300))
        doc.layouts.new("图纸A")
        dxf = base / "测试样本.dxf"
        doc.saveas(dxf)
        before = digest(dxf)
        result = run(dxf, base / "dxf-output")
        assert digest(dxf) == before
        entries = result["drawing"]["entities"]
        assert any(x.get("text") == "CT-02" for x in entries)
        assert any(x.get("text") == "墙面材料说明" for x in entries)
        assert any(x.get("block_name") == "SINK" for x in entries)
        assert any(x["container"] == "block:SINK" and x["type"] == "CIRCLE" for x in entries)
        assert "图纸A" in result["drawing"]["layouts"]

        oda = oda_path(None)
        if oda:
            ezdxf.options.set("odafc-addon", "win_exec_path" if sys.platform == "win32" else "unix_exec_path", str(oda))
            dwg = base / "测试样本.dwg"
            odafc.convert(dxf, dwg, audit=False)
            before = digest(dwg)
            converted = run(dwg, base / "dwg-output")
            assert digest(dwg) == before
            assert any(x.get("text") == "CT-02" for x in converted["drawing"]["entities"])
    print("CAD parser smoke checks passed")


if __name__ == "__main__":
    main()
