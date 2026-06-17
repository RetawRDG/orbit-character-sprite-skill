# Orbit Character Sprite Skill

[English](README.md) | [Русский](README.ru.md)

`orbit-character-sprite` is a Codex skill for creating, auditing, reviewing, and packing fixed-cell character sprite sheets for OrbitSurvive.

The repository root is the skill folder. `SKILL.md` is the file an AI agent must read when the skill is invoked. The Python scripts in `scripts/` are deterministic helpers for pose guides, prompt packs, chroma-key cleanup, sheet audit, first-success validation, review assets, and runtime packing.

## Quick Install Into Codex

From a clean checkout:

```bash
python install.py --force --install-deps
```

This installs the skill into:

```text
$HOME/.agents/skills/orbit-character-sprite
```

For an OrbitSurvive repo-local install:

```powershell
python install.py --scope repo --repo-root R:\Work\OrbitSurvive --force --install-deps
```

More install options, including one-line GitHub install commands, are in [INSTALL.md](INSTALL.md).

## What This Is For

Use this project when working on OrbitSurvive character art:

- player, enemy, boss, and NPC sprite sheets
- four-direction walk cycles
- fixed-cell sheet validation
- image-generation prompt packs from pose-control metadata
- chroma green cleanup
- first-success playable artifact validation
- contact sheets, silhouette sheets, and GIF review packs
- Godot runtime sheets after art is explicitly approved

The skill is intentionally strict. A nice-looking still frame is not enough. A character only passes when identity, motion, scale/cell, visual inspection, and runtime packing all pass separately.

## Repository Layout

```text
.
├── AGENTS.md
├── INSTALL.md
├── SKILL.md
├── README.md
├── README.ru.md
├── install.py
├── requirements.txt
├── agents/
│   └── openai.yaml
├── references/
│   └── first_success_workflow.md
└── scripts/
    ├── audit_walk_sheet.py
    ├── build_approval_pack.py
    ├── build_pose_control_sheet.py
    ├── build_prompt_pack.py
    ├── install_codex_skill.py
    ├── pack_approved_walk_sheet.py
    ├── preview_walk_cycle.py
    ├── selftest_pipeline.py
    ├── validate_first_success.py
    ├── validate_runtime_contract.py
    ├── validate_sheet_contract.py
    ├── core/
    │   ├── __init__.py
    │   └── chroma.py
    └── tests/
        ├── test_audit_thresholds.py
        ├── test_chroma.py
        ├── test_first_success_tools.py
        └── test_install_codex_skill.py
```

`SKILL.md`:
The actual skill instructions. Agents must treat this as the source of truth for the workflow.

`AGENTS.md`:
Repository-level Codex working rules for setup, scope control, validation, and PR reporting.

`install.py` and `scripts/install_codex_skill.py`:
Install this repository into Codex skill scan locations as a user skill or repo-local skill.

`agents/openai.yaml`:
UI metadata for Codex/OpenAI skill lists.

`scripts/core/chroma.py`:
The only source of truth for chroma green detection and cleanup. Do not add a second green-threshold implementation elsewhere.

`scripts/build_pose_control_sheet.py`:
Builds pose-control sheets and per-direction GIFs. These are guides for generation, not candidate art.

`scripts/build_prompt_pack.py`:
Builds deterministic row-level `image_gen` prompts from pose-control metadata.

`scripts/audit_walk_sheet.py`:
Hard gate for generated sheets. Checks fixed grid, visible bounds, edge clipping, height drift, head drift, and foot baseline drift.

`scripts/validate_sheet_contract.py`:
Preflight check for exact sheet dimensions, row count, column count, and expected cell size.

`scripts/build_approval_pack.py`:
Builds review assets after audit passes. This is for human inspection; it is not a substitute for audit.

`scripts/pack_approved_walk_sheet.py`:
Packs approved frame PNGs into a runtime sheet. It may clean, pad, align, and scale, but it must not redraw or hide bad animation.

`scripts/validate_runtime_contract.py`:
Checks runtime frame size, frame count, and required walk row keys against `player_visual.gd`.

`scripts/validate_first_success.py`:
Checks that audit metrics, runtime manifest, runtime sheet, and runtime GIF line up for the first playable handoff.

`scripts/selftest_pipeline.py`:
Synthetic good/bad pipeline check for the scripts.

## Setup

From a clean checkout:

```bash
python -m pip install -r requirements.txt
```

The scripts are plain Python. They currently depend on Pillow; tests use pytest.

## Validation

Run these before pushing changes:

```powershell
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Expected result:

- skill validation passes when the local skill creator validator is available
- all pytest tests pass
- selftest prints `SELFTEST PASS`

The selftest writes temporary files to `outputs/character_sprite/selftest`. `outputs/` is ignored by git.

## How GPT/Codex Agents Should Work Here

When an agent works on this repository:

1. Read `AGENTS.md` and `SKILL.md` first.
2. Keep the skill portable. Do not hardcode local paths such as `R:\Work\OrbitSurvive` unless the code is explicitly reading a user-provided OrbitSurvive checkout.
3. Keep generated outputs, caches, and local review artifacts out of git.
4. Prefer improving scripts over adding long prose to `SKILL.md` when behavior must be deterministic.
5. Keep `SKILL.md` focused on agent procedure. Put human GitHub onboarding details in this README and install details in `INSTALL.md`.
6. After changing chroma behavior, run `python -m pytest scripts\tests` and confirm only `scripts/core/chroma.py` defines `is_key_pixel`.
7. After changing audit, pose, prompt, first-success, or runtime packing behavior, run `python scripts\selftest_pipeline.py`.

Do not claim a character is ready just because a script passes. The skill requires visual review and explicit approval before runtime export.

## Typical OrbitSurvive Workflow

Inside an OrbitSurvive checkout, the skill expects project files such as:

- `GAME_PLAN.md`
- `scripts/core/constants.gd`
- `scripts/entities/player_visual.gd`

For a character run, the agent should create work output under:

```text
outputs/character_sprite/<character_id>_<YYYYMMDD_HHMM>_work/
```

The normal flow is:

1. Record a `run_note.yml`.
2. Build pose-control assets.
3. Build a prompt pack from pose metadata.
4. Generate or receive candidate art.
5. Validate the fixed-cell sheet contract.
6. Audit the fixed-cell sheet.
7. Build a review pack.
8. Ask for explicit approval.
9. Pack runtime frames only after approval.
10. Validate runtime contract and first-success artifacts.

## GitHub Contribution Rules

Before opening a PR or pushing directly:

```powershell
git status -sb
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Commit only source files and intentional metadata. Do not commit:

- `outputs/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- local generated previews

If a change affects OrbitSurvive runtime assumptions, mention the expected consuming files in the PR or commit message, especially `scripts/entities/player_visual.gd`.
