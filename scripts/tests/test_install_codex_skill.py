#!/usr/bin/env python3
"""Tests for the Codex skill installer."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from install_codex_skill import InstallError, copy_skill_payload, normalize_repo, parse_skill_name  # noqa: E402


SKILL_MD = """---
name: orbit-character-sprite
description: test skill
---

# Test skill
"""


class InstallCodexSkillTests(unittest.TestCase):
    def make_source(self, root: Path) -> Path:
        source = root / "source"
        (source / "scripts" / "tests").mkdir(parents=True)
        (source / "references").mkdir()
        (source / "outputs").mkdir()
        (source / ".git").mkdir()
        (source / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        (source / "README.md").write_text("readme", encoding="utf-8")
        (source / "requirements.txt").write_text("Pillow\npytest\n", encoding="utf-8")
        (source / "scripts" / "tool.py").write_text("print('ok')\n", encoding="utf-8")
        (source / "scripts" / "tests" / "test_tool.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
        (source / "references" / "workflow.md").write_text("workflow", encoding="utf-8")
        (source / "outputs" / "generated.png").write_text("do not copy", encoding="utf-8")
        (source / ".git" / "config").write_text("do not copy", encoding="utf-8")
        return source

    def test_parse_skill_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = self.make_source(Path(tmp))
            self.assertEqual(parse_skill_name(source / "SKILL.md"), "orbit-character-sprite")

    def test_copy_payload_excludes_generated_and_git_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            target = root / "target" / "orbit-character-sprite"
            installed = copy_skill_payload(source, target, force=False, dry_run=False)
            self.assertIn("SKILL.md", installed)
            self.assertIn("scripts/tool.py", installed)
            self.assertTrue((target / "SKILL.md").exists())
            self.assertTrue((target / "scripts" / "tool.py").exists())
            self.assertFalse((target / "outputs" / "generated.png").exists())
            self.assertFalse((target / ".git" / "config").exists())

    def test_existing_target_requires_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            target = root / "target" / "orbit-character-sprite"
            target.mkdir(parents=True)
            with self.assertRaises(InstallError):
                copy_skill_payload(source, target, force=False, dry_run=False)

    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_source(root)
            target = root / "target" / "orbit-character-sprite"
            installed = copy_skill_payload(source, target, force=False, dry_run=True)
            self.assertIn("SKILL.md", installed)
            self.assertFalse(target.exists())

    def test_normalize_repo_accepts_url(self) -> None:
        self.assertEqual(
            normalize_repo("https://github.com/RetawRDG/orbit-character-sprite-skill.git"),
            "RetawRDG/orbit-character-sprite-skill",
        )


if __name__ == "__main__":
    unittest.main()
