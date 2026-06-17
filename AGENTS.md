# AGENTS.md

## Repository purpose

This repository is the `orbit-character-sprite` Codex skill for creating, auditing, reviewing, and packing fixed-cell character sprite sheets for OrbitSurvive.

The repository root is the skill folder. `SKILL.md` is the source of truth for the agent workflow. Python scripts under `scripts/` are deterministic helpers and should stay portable.

## Codex working rules

- Read this file and `SKILL.md` before changing behavior.
- Keep diffs minimal and scoped to the requested sprite-skill workflow.
- Do not modify generated outputs, caches, or local review artifacts except inside ignored `outputs/` during local validation.
- Do not hardcode local project paths such as `R:\Work\OrbitSurvive` into scripts.
- Prefer deterministic scripts over expanding prose when a gate or validation rule must be enforced.
- Keep `scripts/core/chroma.py` as the only implementation of chroma-key detection.
- Do not claim a character is ready because one script ran. First success requires candidate art, animation preview, audit, visual review, runtime packing, and runtime contract compatibility.
- Never commit secrets, tokens, credentials, `.env` files, private keys, generated previews, `.import` files, or Godot runtime assets unless the user explicitly asks for integration after approval.

## Setup

```bash
python -m pip install -r requirements.txt
```

## Validation

Run the smallest relevant command after a change:

```bash
python -m pytest scripts/tests
python scripts/selftest_pipeline.py
```

For a full local release check, also run the skill creator validator when it is available in your Codex installation:

```bash
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

If that local validator path is unavailable, say so and still report the pytest and selftest results.

## Change-specific checks

- Chroma changes: run `python -m pytest scripts/tests` and confirm only `scripts/core/chroma.py` defines `is_key_pixel`.
- Audit, pose, prompt, first-success, or runtime packing changes: run `python scripts/selftest_pipeline.py`.
- README or `SKILL.md` changes: check that paths and command examples match the scripts.
- CI changes: keep GitHub Actions dependency installation aligned with `requirements.txt`.

## PR expectations

PR summaries must include:

- changed files;
- why the change matters to the sprite workflow;
- validation commands and results;
- known risks or follow-up work;
- whether runtime export was intentionally skipped or validated.

Do not hide failed validation. A failed gate is useful information, not an invitation to write a more confident sentence.
