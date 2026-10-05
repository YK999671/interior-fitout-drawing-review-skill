"""Small end-to-end checks for the shipped CLI helpers."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script, *args, expected=0):
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *(str(x) for x in args)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected, (script, result.stdout, result.stderr)
    return result


def main():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        source.mkdir()
        drawing = source / "ID-P01.dwg"
        drawing.write_bytes(b"fixture only; not a valid DWG")
        rules = source / "施工说明.txt"
        rules.write_text("墙面基层必须完成防潮处理。\n", encoding="utf-8")
        before = hashlib.sha256(drawing.read_bytes()).hexdigest()

        manifest = base / "manifest.json"
        run("inventory_files.py", source, "-o", manifest)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["file_count"] == 2
        assert next(x for x in data["files"] if x["extension"] == ".dwg")["parse_status"] == "not_attempted"
        assert hashlib.sha256(drawing.read_bytes()).hexdigest() == before

        candidates = base / "candidates.json"
        run("extract_project_rules.py", source, "-o", candidates)
        found = json.loads(candidates.read_text(encoding="utf-8"))
        assert found["candidate_count"] == 1
        assert found["rules"][0]["enabled"] is False
        run("extract_project_rules.py", base / "missing", "-o", candidates, expected=1)

        matrix = base / "coverage.csv"
        run("build_coverage_matrix.py", ROOT / "assets" / "scope-template.csv", "-o", matrix)
        assert "pending_parse" in matrix.read_text(encoding="utf-8-sig")

        issues = base / "issues.json"
        issues.write_text(json.dumps({"issues": []}), encoding="utf-8")
        run("validate_issue_register.py", issues)

    print("smoke checks passed")


if __name__ == "__main__":
    main()
