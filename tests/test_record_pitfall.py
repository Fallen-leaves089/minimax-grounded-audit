from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
RECORDER = ROOT / "scripts" / "record_pitfall.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_skill(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "references").mkdir(exist_ok=True)
    manifest = {
        "schema_version": 1,
        "name": "project-health-audit",
        "package_name": "minimax-grounded-audit",
        "version": "0.1.0",
        "license": "Apache-2.0",
        "memory": {
            "mode": "external",
            "directory": "$MINIMAX_DATA_DIR/skill-memory/project-health-audit",
            "local": "PITFALLS.local.md",
        },
        "runtime_required_files": [
            "SKILL.md",
            "skill.json",
            "references/report-template.md",
            "scripts/record_pitfall.py",
        ],
    }
    write_text(root / "skill.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_text(
        root / "SKILL.md",
        "---\n"
        "name: project-health-audit\n"
        "description: test skill\n"
        "license: Apache-2.0\n"
        "metadata:\n"
        "  version: 0.1.0\n"
        "---\n\n"
        "# Test\n",
    )
    write_text(root / "references" / "report-template.md", "# Report\n")
    shutil.copy2(RECORDER, root / "scripts" / "record_pitfall.py")


def load_recorder(root: Path):
    name = f"recorder_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / "record_pitfall.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load recorder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RecordPitfallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "minimax-grounded-audit"
        self.memory_dir = self.base / "memory"
        make_skill(self.root)
        self.mod = load_recorder(self.root)

    def entry(self, **overrides: str):
        values = {
            "tag": "host:minimax-code,model:minimax,test",
            "trigger": "when a check is claimed without execution",
            "wrong": "reporting a pass without evidence",
            "right": "run the command and record exit code and output",
            "verify": "positive and negative fixtures both behaved as expected",
        }
        values.update(overrides)
        return self.mod.Entry(**values)

    def memory(self) -> Path:
        return self.memory_dir / "PITFALLS.local.md"

    def test_external_memory_is_created_and_appended(self) -> None:
        result = self.mod.record(
            self.root,
            self.entry(),
            memory_dir=self.memory_dir,
            record_date="2026-01-01",
        )
        self.assertEqual(result.status, "appended")
        text = self.memory().read_text(encoding="utf-8")
        self.assertIn("MiniMax Code 本地审计记忆", text)
        self.assertIn("2026-01-01 | host:minimax-code", text)
        self.assertIn("positive and negative fixtures", text)
        self.assertFalse((self.root / "PITFALLS.local.md").exists())

    def test_exact_duplicate_is_noop_and_newer_date_refreshes_only_date(self) -> None:
        first = self.mod.record(
            self.root,
            self.entry(),
            memory_dir=self.memory_dir,
            record_date="2026-01-01",
        )
        self.assertEqual(first.status, "appended")
        duplicate = self.mod.record(
            self.root,
            self.entry(),
            memory_dir=self.memory_dir,
            record_date="2026-01-01",
        )
        self.assertEqual(duplicate.status, "duplicate")
        self.assertEqual(self.memory().read_text(encoding="utf-8").count("2026-01-01"), 1)

        refreshed = self.mod.record(
            self.root,
            self.entry(),
            memory_dir=self.memory_dir,
            record_date="2026-02-01",
        )
        self.assertEqual(refreshed.status, "updated")
        text = self.memory().read_text(encoding="utf-8")
        self.assertIn("2026-02-01", text)
        self.assertNotIn("2026-01-01", text)
        self.assertEqual(text.count("host:minimax-code"), 1)

    def test_dry_run_does_not_create_memory_directory(self) -> None:
        result = self.mod.record(
            self.root,
            self.entry(),
            memory_dir=self.memory_dir,
            dry_run=True,
        )
        self.assertEqual(result.status, "dry-run")
        self.assertFalse(self.memory_dir.exists())

    def test_parent_is_recorded(self) -> None:
        result = self.mod.record(
            self.root,
            self.entry(parent="TEST-02"),
            memory_dir=self.memory_dir,
            record_date="2026-01-01",
        )
        self.assertEqual(result.status, "appended")
        self.assertIn("父条目 TEST-02", self.memory().read_text(encoding="utf-8"))

    def test_default_memory_uses_minimax_data_dir(self) -> None:
        home = self.base / "minimax-data"
        with mock.patch.dict(
            os.environ,
            {"MINIMAX_DATA_DIR": str(home), "MINIMAX_SKILL_MEMORY_DIR": "", "MAVIS_DATA_DIR": ""},
            clear=False,
        ):
            result = self.mod.record(
                self.root,
                self.entry(),
                record_date="2026-01-01",
            )
        expected = home / "skill-memory" / "project-health-audit" / "PITFALLS.local.md"
        self.assertEqual(result.path, expected)
        self.assertTrue(expected.is_file())

    def test_default_memory_falls_back_to_mavis_data_dir(self) -> None:
        home = self.base / "mavis-data"
        with mock.patch.dict(
            os.environ,
            {"MINIMAX_DATA_DIR": "", "MINIMAX_SKILL_MEMORY_DIR": "", "MAVIS_DATA_DIR": str(home)},
            clear=False,
        ):
            result = self.mod.record(
                self.root,
                self.entry(),
                record_date="2026-01-01",
            )
        expected = home / "skill-memory" / "project-health-audit" / "PITFALLS.local.md"
        self.assertEqual(result.path, expected)
        self.assertTrue(expected.is_file())

    def test_memory_directory_overlapping_skill_root_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.root / "memory",
                dry_run=True,
            )

    def test_sensitive_values_are_rejected(self) -> None:
        values = (
            "sk-" + "a" * 24,
            "person" + "@" + "example.com",
            "192.168." + "1.10",
            "C:\\Users\\" + "Alice\\project",
        )
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.mod.record(
                        self.root,
                        self.entry(trigger=value),
                        memory_dir=self.memory_dir,
                        dry_run=True,
                    )

    def test_invalid_fields_are_rejected(self) -> None:
        for field, value in (
            ("trigger", ""),
            ("wrong", "line\nbreak"),
            ("right", "a | b"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.mod.record(
                        self.root,
                        self.entry(**{field: value}),
                        memory_dir=self.memory_dir,
                        dry_run=True,
                    )

    def test_root_fingerprint_rejects_manifest_mismatch(self) -> None:
        manifest = json.loads((self.root / "skill.json").read_text(encoding="utf-8"))
        manifest["name"] = "other-skill"
        write_text(self.root / "skill.json", json.dumps(manifest) + "\n")
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_root_fingerprint_rejects_package_mismatch(self) -> None:
        manifest = json.loads((self.root / "skill.json").read_text(encoding="utf-8"))
        manifest["package_name"] = "other-package"
        write_text(self.root / "skill.json", json.dumps(manifest) + "\n")
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_missing_runtime_file_is_rejected(self) -> None:
        (self.root / "references" / "report-template.md").unlink()
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_external_recorder_is_rejected(self) -> None:
        other = self.base / "other_recorder.py"
        shutil.copy2(RECORDER, other)
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
                recorder_path=other,
            )

    def test_manifest_path_escape_is_rejected(self) -> None:
        manifest = json.loads((self.root / "skill.json").read_text(encoding="utf-8"))
        manifest["runtime_required_files"].append("../outside.md")
        write_text(self.root / "skill.json", json.dumps(manifest) + "\n")
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_bom_memory_is_rejected(self) -> None:
        write_text(self.memory(), "# memory\n")
        self.memory().write_bytes(b"\xef\xbb\xbf# memory\n")
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_symlink_memory_is_rejected_when_supported(self) -> None:
        self.memory_dir.mkdir(parents=True)
        outside = self.base / "outside.md"
        outside.write_text("# outside\n", encoding="utf-8")
        try:
            os.symlink(outside, self.memory())
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is not available in this environment")
        with self.assertRaises(ValueError):
            self.mod.record(
                self.root,
                self.entry(),
                memory_dir=self.memory_dir,
                dry_run=True,
            )

    def test_cli_exit_codes(self) -> None:
        script = self.root / "scripts" / "record_pitfall.py"
        base = [
            sys.executable,
            "-B",
            str(script),
            "--root",
            str(self.root),
            "--memory-dir",
            str(self.memory_dir),
            "--trigger",
            "trigger",
            "--wrong",
            "wrong",
            "--right",
            "right",
            "--verify",
            "verify",
        ]
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        dry = subprocess.run(
            base + ["--tag", "host:minimax-code", "--dry-run"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("DRY-RUN", dry.stdout)

        invalid = subprocess.run(
            base + ["--tag", ""],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        self.assertEqual(invalid.returncode, 1)
        self.assertIn("ERROR", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
