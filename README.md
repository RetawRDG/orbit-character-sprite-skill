# Orbit Character Sprite Skill

[English](README.md) | [Русский](README.ru.md)

`orbit-character-sprite` is a Codex skill for creating, auditing, reviewing, and packing fixed-cell character sprite sheets for OrbitSurvive.

The repository root is the skill folder. `SKILL.md` is the file an AI agent must read when the skill is invoked. The Python scripts in `scripts/` are deterministic helpers for pose guides, chroma-key cleanup, sheet audit, review assets, and runtime packing.

## What This Is For

Use this project when working on OrbitSurvive character art:

- player, enemy, boss, and NPC sprite sheets
- four-direction walk cycles
- fixed-cell sheet validation
- chroma green cleanup
- contact sheets, silhouette sheets, and GIF review packs
- Godot runtime sheets after art is explicitly approved

The skill is intentionally strict. A nice-looking still frame is not enough. A character only passes when identity, motion, scale/cell, visual inspection, and runtime packing all pass separately.

## Repository Layout

```text
.
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
└── scripts/
    ├── audit_walk_sheet.py
    ├── build_approval_pack.py
    ├── build_pose_control_sheet.py
    ├── pack_approved_walk_sheet.py
    ├── preview_walk_cycle.py
    ├── selftest_pipeline.py
    ├── core/
    │   ├── __init__.py
    │   └── chroma.py
    └── tests/
        ├── test_audit_thresholds.py
        └── test_chroma.py
```

`SKILL.md`:
The actual skill instructions. Agents must treat this as the source of truth for the workflow.

`agents/openai.yaml`:
UI metadata for Codex/OpenAI skill lists.

`scripts/core/chroma.py`:
The only source of truth for chroma green detection and cleanup. Do not add a second green-threshold implementation elsewhere.

`scripts/build_pose_control_sheet.py`:
Builds pose-control sheets and per-direction GIFs. These are guides for generation, not candidate art.

`scripts/audit_walk_sheet.py`:
Hard gate for generated sheets. Checks fixed grid, visible bounds, edge clipping, height drift, head drift, and foot baseline drift.

`scripts/build_approval_pack.py`:
Builds review assets after audit passes. This is for human inspection; it is not a substitute for audit.

`scripts/pack_approved_walk_sheet.py`:
Packs approved frame PNGs into a runtime sheet. It may clean, pad, align, and scale, but it must not redraw or hide bad animation.

`scripts/selftest_pipeline.py`:
Synthetic good/bad pipeline check for the scripts.

## Setup

From a clean checkout:

```powershell
cd R:\Work\orbit-character-sprite-skill
python -m pip install pillow pytest
```

The scripts are plain Python. They currently depend on Pillow; tests use pytest.

## Validation

Run these before pushing changes:

```powershell
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py R:\Work\orbit-character-sprite-skill
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Expected result:

- skill validation passes
- all pytest tests pass
- selftest prints `SELFTEST PASS`

The selftest writes temporary files to `outputs/character_sprite/selftest`. `outputs/` is ignored by git.

## How GPT/Codex Agents Should Work Here

When an agent works on this repository:

1. Read `SKILL.md` first.
2. Keep the skill portable. Do not hardcode local paths such as `R:\Work\OrbitSurvive` unless the code is explicitly reading a user-provided OrbitSurvive checkout.
3. Keep generated outputs, caches, and local review artifacts out of git.
4. Prefer improving scripts over adding long prose to `SKILL.md` when behavior must be deterministic.
5. Keep `SKILL.md` focused on agent procedure. Put human GitHub onboarding details in this README.
6. After changing chroma behavior, run `python -m pytest scripts\tests` and confirm only `scripts/core/chroma.py` defines `is_key_pixel`.
7. After changing audit, pose, or runtime packing behavior, run `python scripts\selftest_pipeline.py`.

Do not claim a character is ready just because a script passes. The skill requires visual review and explicit approval before runtime export.

## Installing Back Into Codex

Clone the repository into a skill folder named `orbit-character-sprite`:

```powershell
git clone https://github.com/RetawRDG/orbit-character-sprite-skill.git C:\Users\retaw\.codex\skills\orbit-character-sprite
```

For OrbitSurvive repo-local usage, copy or clone it under:

```powershell
R:\Work\OrbitSurvive\.agents\skills\orbit-character-sprite
```

After installing, restart/reload the Codex session so the skill list is refreshed.

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
3. Generate or receive candidate art.
4. Audit the fixed-cell sheet.
5. Build a review pack.
6. Ask for explicit approval.
7. Pack runtime frames only after approval.

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
