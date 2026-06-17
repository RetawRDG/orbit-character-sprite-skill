# First Success Workflow

Use this checklist when a character run is meant to become playable in OrbitSurvive, not merely pretty in a chat preview.

## Minimum playable gate

A first-success character requires all of these:

1. One approved identity reference.
2. Pose-control assets for the intended rows and frame count.
3. A prompt pack generated from the pose-control metadata.
4. Candidate walk rows on an exact fixed-cell sheet.
5. A fixed-grid preflight check with `validate_sheet_contract.py`.
6. A normal audit pass from `audit_walk_sheet.py`.
7. Human visual review of the contact sheet, silhouette sheet, and row GIFs.
8. Runtime export from approved frames only.
9. Runtime contract validation against `player_visual.gd` when the game checkout is available.
10. First-success validation against audit metrics, runtime manifest, runtime sheet, and runtime GIF.

## Useful commands

```powershell
python .agents\skills\orbit-character-sprite\scripts\build_prompt_pack.py `
  --pose-json outputs\character_sprite\<character_id>_work\<prefix>_pose_control.json `
  --out-dir outputs\character_sprite\<character_id>_work\prompts `
  --prefix <character_id>
```

```powershell
python .agents\skills\orbit-character-sprite\scripts\validate_sheet_contract.py `
  --input outputs\character_sprite\<character_id>_work\<sheet>.png `
  --rows down,right,up,left `
  --cols 6 `
  --cell-width 96 `
  --cell-height 96
```

```powershell
python .agents\skills\orbit-character-sprite\scripts\validate_runtime_contract.py `
  --runtime-gd scripts\entities\player_visual.gd `
  --manifest outputs\character_sprite\<character_id>_work\runtime_review\<character_id>_approved_manifest.json
```

```powershell
python .agents\skills\orbit-character-sprite\scripts\validate_first_success.py `
  --work-dir outputs\character_sprite\<character_id>_work `
  --prefix <character_id> `
  --rows down,right,up,left `
  --frames 6 `
  --audit-metrics outputs\character_sprite\<character_id>_work\audit\<character_id>_audit_metrics.json `
  --runtime-manifest outputs\character_sprite\<character_id>_work\runtime_review\<character_id>_approved_manifest.json `
  --runtime-sheet outputs\character_sprite\<character_id>_work\runtime_review\<character_id>_approved_runtime_sheet.png `
  --runtime-gif outputs\character_sprite\<character_id>_work\runtime_review\<character_id>_approved_walk.gif
```

## Non-goals

These checks do not prove artistic quality. They prove that the generated files are shaped, counted, and packaged in a way the runtime can consume after a human approves the actual motion and pixels.
