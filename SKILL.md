---
name: orbit-character-sprite
description: Use when creating, repairing, or reviewing OrbitSurvive character sprites, player/enemy/NPC sprite sheets, walk cycles, direction views, silhouettes, weapon overlays, normal maps, Godot runtime sheets, chroma-key cleanup, or complaints that character art looks inconsistent, noisy, flat, cropped, jittery, or ugly.
---

# Orbit Character Sprite

## Core Principle

Accept a character only when four gates pass separately: `identity`, `motion`, `scale/cell`, and `runtime`. A pretty still frame can pass identity and still fail as a game character.

Use the current project as truth. Read `GAME_PLAN.md`, `scripts/core/constants.gd`, and the consuming runtime script before generation or export. In this project `PLAYER_W/PLAYER_H` are collision-scale constants; the current player visual runtime contract lives in `scripts/entities/player_visual.gd` (`FRAME_SIZE`, `FRAME_COUNT`, `TARGET_HEIGHT`, row map). Do not hardcode stale values such as old 128px runtime cells.

All exploration output goes under `outputs/character_sprite/...`. Do not write `assets/art/player*.png`, `.import`, scenes, or runtime assets until the user explicitly asks for integration after the gates pass.

## Generation Engine

The selected generator for this skill is the built-in `image_gen` available in the chat environment. Do not invent model versions, API features, prices, or seeds. If `image_gen` cannot accept the required reference/pose conditioning in the active environment, stop and report that generation is blocked instead of faking a pipeline.

Use `image_gen` as image-to-image/reference-conditioned generation:

- Input identity: one approved or user-provided `identity_reference` image. Treat it as style/silhouette/material guidance, not source pixels to reuse 1:1.
- Input pose: the pose-control sheet from `scripts/build_pose_control_sheet.py`. It is a control guide, not candidate art.
- Output: fresh rendered frames or rows in fixed cells on pure chroma green.
- Repro note: record generator family (`GPT Image / image_gen`), prompt, conditioning images, frame/row name, and any exposed seed/settings in `run_note.yml`; if seed/settings are not exposed, write `unavailable`.

Prompt by frame/row, not by vague sheet wish. Ask for "same approved character, frame N of walk/down, fixed cell, full body visible, pure green background" and include the exact gait phase from the pose-control metadata.

## Run Note Contract

Create `outputs/character_sprite/<character_id>_<YYYYMMDD_HHMM>_work/run_note.yml` before generation:

- `character_id`
- `identity_reference`
- `fresh_run: true`
- `generator: image_gen`
- `constants_gd`: viewport, tile size, player collision constants
- `runtime_contract`: script path, frame size, frame count, target height, row map
- `symmetric: true|false`
- `mass_class`: light, medium, heavy, bulky, floating, crawler, etc.
- `gait_style`: short heavy stride, fast light run, limp, hover-bob, etc.
- `palette_constraints`: include colors that must survive chroma-key, especially cyan/teal lights
- every image path classified as `identity_reference`, `pose_control`, `fresh_generated_source`, `approved_source`, `diagnostic_output`, or `negative_example`

## Reference Case: Asymmetric Astronaut

For the supplied astronaut-on-green reference:

- Classify the image as `identity_reference`, not source art.
- Preserve the design language at game scale: bulky worn suit, amber visor, blue-gray armor, backpack/tubes, teal lights, heavy boots, material contrast, rim light.
- Simplify details for low-res gameplay; do not reproduce the large reference 1:1.
- Set `symmetric: false` because skull shoulder mark and pouches are asymmetric.
- Do not mirror `right` to make `left`; draw both side directions separately.
- Chroma-key must preserve saturated cyan/teal lights.

This case is an example, not a global rule. Other characters define their own mass class, gait, palette, and symmetry.

## Gate Order

1. `identity`: one fresh down/front neutral frame reads as the requested character at game scale.
2. `pose`: pose-control GIF walks correctly before art is generated.
3. `motion`: a rendered row animates with believable support foot, swing foot, weight transfer, and arm opposition according to `mass_class` and `gait_style`.
4. `scale/cell`: raw generated pixels pass `audit_walk_sheet.py` in fixed cells.
5. `visual truth`: inspect actual pixels/GIF for cropped helmet/boots, missing legs, extra heads, duplicated parts, green fringe, shadows, size drift, or character drift.
6. `runtime`: pack only approved fixed-cell frames using the current runtime contract.

Passing one gate never implies another. Packer success is not motion success.

## Canonical Stop List

Stop immediately and repair the current frame/row if any item is true:

- Old generated rows/sheets are reused as fresh source art without explicit user approval.
- A diagnostic blockout, skeleton, or pose-control sheet is presented as candidate character art.
- The row looks expensive but the walk is random, sliding, scissoring, floating, or disconnected from pelvis/center of mass.
- Body height, helmet size, backpack, boots, or baseline drift between frames/directions.
- Any visible character pixel touches the source cell edge unless the user explicitly accepts the crop.
- Head, boots, weapon, backpack, or limbs are clipped.
- Side/up/down views look like different characters.
- Cyan/teal emissive pixels are removed by chroma-key.
- A row only looks aligned because each frame used a different crop/box.
- The user has not seen the candidate art/GIF that would be exported.
- A gate fails while `--warn-only` hides the nonzero exit code.

`--warn-only` is for investigation only. Gate commands must run without `--warn-only`.

## Chroma Contract

All scripts must use `scripts/core/chroma.py` for key detection and cleanup. Do not reimplement local green thresholds. Cyan/teal lights are character pixels and must survive cleanup.

Run after chroma changes:

```powershell
python .agents\skills\orbit-character-sprite\scripts\tests\test_chroma.py
rg -n "def is_key_pixel" .agents\skills\orbit-character-sprite\scripts
```

Only `scripts/core/chroma.py` should define `is_key_pixel`.

## Pose-Control Contract

Pose-control is an internal guide, not art. It must use the same rows, frame count, cell size, baseline, head guide, support foot, swing foot, and gait labels expected from generation.

Current low-res defaults are candidate cells of `96x96` and target body height near `64px`, then runtime pack reads the actual frame size from `player_visual.gd`.

```powershell
python .agents\skills\orbit-character-sprite\scripts\build_pose_control_sheet.py `
  --out-dir outputs\character_sprite\<character_id>_work `
  --prefix <character_id>_walk_pose_control `
  --rows down,right,up,left `
  --frames 6 `
  --cell-width 96 `
  --cell-height 96 `
  --target-body-height 64
```

Watch the per-direction pose GIFs before calling `image_gen`. If the guide does not walk, final art will not walk.

## Image Generation Runbook

1. Save the user reference path in `run_note.yml` as `identity_reference`.
2. Generate one fresh `down/front neutral` identity frame using `image_gen`.
3. Show only the candidate rendered frame, not the pose-control diagnostic.
4. After approval, generate `walk/down` against the approved identity frame plus the `down` pose-control row.
5. Audit the raw row before making review packs.
6. If `walk/down` passes, repeat `right`, `up`, `left`. For `symmetric: false`, do not mirror.
7. Combine approved rows into a fixed-cell sheet.
8. Audit combined sheet.
9. Build contact/silhouette/GIF review assets.
10. Pack runtime only from approved frames and only to `outputs/`.

When generation fails a gate, regenerate or repair that row only. Do not pack, resize, mirror, crop, shadow, weapon-overlay, or Godot-bob a bad gait into looking acceptable.

## Audit Gate

Use grid mode by default for detailed/generated art. `auto` is cell-local and exploratory; it must not be a substitute for a known fixed grid.

```powershell
python .agents\skills\orbit-character-sprite\scripts\audit_walk_sheet.py `
  --input outputs\character_sprite\<character_id>_work\<sheet>.png `
  --out-dir outputs\character_sprite\<character_id>_work\audit `
  --prefix <character_id>_audit `
  --rows down,right,up,left `
  --cols 6 `
  --mode grid `
  --anchor-row down `
  --max-direction-height-drift 0.05 `
  --max-frame-height-drift 0.10 `
  --max-baseline-drift-ratio 0.12 `
  --max-head-drift-ratio 0.12 `
  --constants-gd scripts\core\constants.gd
```

Absolute overrides such as `--max-baseline-drift` and `--max-head-drift` exist only for investigation or legacy comparison. Prefer ratio thresholds so the same relative drift fails at both small and larger cells.

## Review Pack

Build review assets only after audit passes. This pack is visual, not a scale gate.

```powershell
python .agents\skills\orbit-character-sprite\scripts\build_approval_pack.py `
  --input outputs\character_sprite\<character_id>_work\<sheet>.png `
  --out-dir outputs\character_sprite\<character_id>_work\review `
  --prefix <character_id>_review `
  --rows down,right,up,left `
  --cols 6 `
  --cell-width 96 `
  --cell-height 96
```

Show the user the rendered contact sheet and sequential GIF/strip. If GIF colors drift, use the PNG strip as the color reference.

## Approval Lock

Only explicit user approval creates `approved_source`.

When approved:

- Copy exact approved frames into `outputs/character_sprite/approved_reference/`.
- Record canvas size, frame order, foot anchors, head tops, body height, tight bboxes, source file, and approval note.
- Derive later sheets from approved files, not chat memory or old previews.
- If one frame or row fails later, regenerate that missing piece only unless identity drifted.

## Runtime Export

Runtime export is mechanical. It may clean chroma, pad, align by foot anchor, scale with nearest, pack rows, and generate review GIFs. It may not redraw anatomy, change gait, add shadows, add weapons, resize per direction, or use Godot `flip_h` to hide missing art.

Use the current runtime script to obtain frame size:

```powershell
python .agents\skills\orbit-character-sprite\scripts\pack_approved_walk_sheet.py `
  --input-dir outputs\character_sprite\approved_reference `
  --out-dir outputs\character_sprite\<character_id>_work\runtime_review `
  --prefix <character_id> `
  --rows down,right,up,left `
  --frames 6 `
  --runtime-gd scripts\entities\player_visual.gd `
  --resample nearest
```

For current `player_visual.gd`, final in-game integration needs the full runtime row contract:

- `FRAME_SIZE` from script, currently `96x96`.
- `FRAME_COUNT`, currently `6`.
- Rows from `ROWS`: idle, walk, shoot, long_idle, hit by down/right/up/left.
- Walk rows map to `walk_down`, `walk_right`, `walk_up`, `walk_left`.
- Non-walk rows must be drawn or explicitly duplicated only after the body walk is approved.

Keep Godot import sharp: nearest/filter off, mipmaps off, no unintended compression, no per-direction `flip_h` for asymmetric characters. Symmetric characters may use one consistent mirror policy (`symmetric: true` permits art mirroring or runtime flip; `symmetric: false` forbids both).

## Visual Truth Review

Before any runtime handoff, open the actual candidate sheet/GIF and answer in `run_note.yml`:

- Does it still match the identity reference after simplification?
- Does it move according to the declared mass/gait?
- Are support and swing feet coherent in every frame?
- Are helmet, body, backpack, boots, and palette stable?
- Are there any clipped parts, leftovers, green fringe, floating shadows, duplicate limbs, or direction scale changes?
- Does it read at OrbitSurvive camera scale?

If any answer is no, runtime is `blocked`.

## Good/Bad Selftest

The skill includes a synthetic golden/negative pipeline test:

```powershell
python .agents\skills\orbit-character-sprite\scripts\selftest_pipeline.py
```

Expected behavior:

- `selftest_good_sheet.png` passes pose-control, audit, and pack.
- `selftest_bad_sheet.png` fails audit with exit code `2`.
- Outputs land in `outputs/character_sprite/selftest`.

This proves script mechanics only. It does not approve artistic quality.

## Script Roles

- `scripts/core/chroma.py`: one source of truth for chroma-key and spill cleanup.
- `scripts/build_pose_control_sheet.py`: fixed-cell motion guide.
- `scripts/audit_walk_sheet.py`: hard gate for cell, scale, baseline, head drift, edge clipping, and metrics.
- `scripts/build_approval_pack.py`: visual review pack after audit; can hide source mistakes, so it is not proof.
- `scripts/pack_approved_walk_sheet.py`: output-only runtime packer from approved frames.
- `scripts/selftest_pipeline.py`: synthetic green/red pipeline check.
- `scripts/preview_walk_cycle.py`: old diagnostic placeholder only; never candidate art.

## Final Handoff

Report:

- generator used and whether seed/settings were exposed
- identity/motion/scale/runtime gate status
- first artifact to inspect
- failed gate and exact reason, if blocked
- whether runtime export was intentionally skipped

Do not say the character is ready because a script ran. Say ready only when candidate art, motion, metrics, visual truth, and the target runtime contract all pass.
