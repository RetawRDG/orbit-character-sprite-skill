#!/usr/bin/env python3
"""Install this repository as a local Codex skill.

The repository root is the skill folder. This installer copies the portable skill
payload into one of the Codex skill scan locations, usually:

- user scope: $HOME/.agents/skills/orbit-character-sprite
- repo scope: <repo-root>/.agents/skills/orbit-character-sprite
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

SKILL_NAME = "orbit-character-sprite"
DEFAULT_REF = "main"
INCLUDE_FILES = {
    "SKILL.md",
    "README.md",
    "README.ru.md",
    "INSTALL.md",
    "AGENTS.md",
    "requirements.txt",
}
INCLUDE_DIRS = {
    "agents",
    "assets",
    "references",
    "scripts",
}
EXCLUDE_DIR_NAMES = {
    ".git",
    ".github",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "outputs",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
}


class InstallError(RuntimeError):
    """Raised when installation cannot continue safely."""


def parse_skill_name(skill_md: Path) -> str:
    if not skill_md.exists():
        raise InstallError(f"missing SKILL.md at {skill_md}")
    in_frontmatter = False
    for raw_line in skill_md.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            break
        if in_frontmatter and line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"\'')
    raise InstallError(f"SKILL.md at {skill_md} has no frontmatter name")


def find_local_source() -> Path:
    candidates: list[Path] = []
    if "__file__" in globals():
        script_path = Path(__file__).resolve()
        candidates.extend([script_path.parent.parent, script_path.parent, Path.cwd()])
    else:
        candidates.append(Path.cwd())
    for candidate in candidates:
        if (candidate / "SKILL.md").exists():
            return candidate
    raise InstallError("could not infer source skill root; pass --source or --from-github")


def normalize_repo(value: str) -> str:
    repo = value.strip()
    if repo.startswith("https://github.com/"):
        repo = repo.removeprefix("https://github.com/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    repo = repo.strip("/")
    parts = repo.split("/")
    if len(parts) != 2 or not all(parts):
        raise InstallError("--from-github must look like owner/repo or https://github.com/owner/repo")
    return repo


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def clone_from_github(repo: str, ref: str, parent: Path) -> Path:
    normalized = normalize_repo(repo)
    destination = parent / "source"
    if command_exists("git"):
        url = f"https://github.com/{normalized}.git"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, url, str(destination)],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            return destination
        # Fall through to zip download for environments without usable git refs.
    owner, name = normalized.split("/", 1)
    zip_url = f"https://codeload.github.com/{owner}/{name}/zip/refs/heads/{ref}"
    zip_path = parent / "source.zip"
    try:
        urllib.request.urlretrieve(zip_url, zip_path)
    except Exception as exc:  # pragma: no cover - network behavior is environment-dependent.
        raise InstallError(f"failed to download {zip_url}: {exc}") from exc
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(parent)
    extracted = [item for item in parent.iterdir() if item.is_dir() and item.name.startswith(f"{name}-")]
    if not extracted:
        raise InstallError("downloaded GitHub archive did not contain a repository folder")
    return extracted[0]


def default_target(scope: str, repo_root: Path | None) -> Path:
    if scope == "user":
        return Path.home() / ".agents" / "skills" / SKILL_NAME
    if repo_root is None:
        raise InstallError("--repo-root is required when --scope repo is used")
    return repo_root.resolve() / ".agents" / "skills" / SKILL_NAME


def should_copy(path: Path, source: Path) -> bool:
    relative = path.relative_to(source)
    parts = relative.parts
    if not parts:
        return True
    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return False
    if path.is_dir():
        return parts[0] in INCLUDE_DIRS
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    if len(parts) == 1:
        return path.name in INCLUDE_FILES
    return parts[0] in INCLUDE_DIRS


def copy_skill_payload(source: Path, destination: Path, force: bool, dry_run: bool) -> list[str]:
    source = source.resolve()
    destination = destination.resolve()
    skill_name = parse_skill_name(source / "SKILL.md")
    if skill_name != SKILL_NAME:
        raise InstallError(f"SKILL.md name {skill_name!r} does not match installer skill name {SKILL_NAME!r}")

    selected: list[Path] = []
    for item in source.rglob("*"):
        if should_copy(item, source):
            selected.append(item)
    files = [item for item in selected if item.is_file()]
    if not files:
        raise InstallError(f"no files selected from {source}")

    installed_paths = [str(path.relative_to(source)) for path in files]
    if dry_run:
        return installed_paths

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not force:
            raise InstallError(f"target already exists: {destination}. Re-run with --force to replace it.")
        shutil.rmtree(destination)
    staging = destination.with_name(f".{destination.name}.installing")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        for path in files:
            relative = path.relative_to(source)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return installed_paths


def install_dependencies(target: Path) -> None:
    requirements = target / "requirements.txt"
    if not requirements.exists():
        print("No requirements.txt found in installed skill; skipping dependency install.")
        return
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements)], text=True)
    if result.returncode != 0:
        raise InstallError("dependency installation failed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install orbit-character-sprite into a Codex skill scan location.")
    parser.add_argument("--source", type=Path, default=None, help="Local skill repository root. Defaults to this checkout.")
    parser.add_argument("--from-github", default=None, help="Clone/download a GitHub repo first, e.g. RetawRDG/orbit-character-sprite-skill.")
    parser.add_argument("--ref", default=DEFAULT_REF, help="Git branch or tag to install when --from-github is used.")
    parser.add_argument("--scope", choices=["user", "repo"], default="user", help="Install to user skills or a repository-local skills folder.")
    parser.add_argument("--repo-root", type=Path, default=None, help="Repository root when --scope repo is used.")
    parser.add_argument("--target", type=Path, default=None, help="Explicit target directory. Overrides --scope and --repo-root.")
    parser.add_argument("--force", action="store_true", help="Replace an existing installed skill directory.")
    parser.add_argument("--dry-run", action="store_true", help="Show selected files without writing anything.")
    parser.add_argument("--install-deps", action="store_true", help="Run pip install -r requirements.txt after copying.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if args.from_github:
            temp_dir = tempfile.TemporaryDirectory()
            source = clone_from_github(args.from_github, args.ref, Path(temp_dir.name))
        else:
            source = (args.source or find_local_source()).resolve()
        target = (args.target.resolve() if args.target else default_target(args.scope, args.repo_root))
        installed = copy_skill_payload(source, target, args.force, args.dry_run)
        action = "Would install" if args.dry_run else "Installed"
        print(f"{action} {SKILL_NAME} -> {target}")
        print(f"Files: {len(installed)}")
        if args.dry_run:
            for path in installed:
                print(f"- {path}")
        if args.install_deps and not args.dry_run:
            install_dependencies(target)
        if not args.dry_run:
            print("Codex scans this location automatically. Restart Codex if the skill does not appear immediately.")
            print("Try: use $orbit-character-sprite to review a fixed-cell character walk sheet.")
        return 0
    except InstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
