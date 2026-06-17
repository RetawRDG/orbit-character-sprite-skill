# Install Orbit Character Sprite as a Codex skill

Codex skills are discovered from `.agents/skills` locations. This repository is already shaped as a skill folder: the repository root contains `SKILL.md`, `scripts/`, `references/`, and `agents/openai.yaml`.

## Recommended one-command install after cloning

From the repository root:

```bash
python install.py --force --install-deps
```

This installs the skill into:

```text
$HOME/.agents/skills/orbit-character-sprite
```

Use this for a personal Codex skill that should be available from any project.

## Install directly from GitHub

After this branch is merged to `main`, run one of these commands.

PowerShell:

```powershell
$dir = Join-Path $env:TEMP "orbit-character-sprite-skill"; if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }; git clone https://github.com/RetawRDG/orbit-character-sprite-skill.git $dir; python $dir\install.py --force --install-deps
```

Bash:

```bash
tmp="$(mktemp -d)" && git clone https://github.com/RetawRDG/orbit-character-sprite-skill.git "$tmp/orbit-character-sprite-skill" && python "$tmp/orbit-character-sprite-skill/install.py" --force --install-deps
```

## Install this draft PR branch directly

Use this while PR `codex-sprite-skill-hardening` is not merged yet.

PowerShell:

```powershell
$dir = Join-Path $env:TEMP "orbit-character-sprite-skill"; if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }; git clone --branch codex-sprite-skill-hardening https://github.com/RetawRDG/orbit-character-sprite-skill.git $dir; python $dir\install.py --force --install-deps
```

Bash:

```bash
tmp="$(mktemp -d)" && git clone --branch codex-sprite-skill-hardening https://github.com/RetawRDG/orbit-character-sprite-skill.git "$tmp/orbit-character-sprite-skill" && python "$tmp/orbit-character-sprite-skill/install.py" --force --install-deps
```

## Install into an OrbitSurvive checkout

Use repo scope when the skill should travel with the game repository instead of your user account:

```powershell
python install.py --scope repo --repo-root R:\Work\OrbitSurvive --force --install-deps
```

This writes:

```text
R:\Work\OrbitSurvive\.agents\skills\orbit-character-sprite
```

## Dry run

Preview the files without changing anything:

```bash
python install.py --dry-run
```

## Verify

Check that the required skill file exists:

```bash
python -c "from pathlib import Path; p=Path.home()/'.agents'/'skills'/'orbit-character-sprite'/'SKILL.md'; print(p, p.exists())"
```

Then restart Codex if the skill does not appear immediately. In Codex CLI or IDE, use `/skills` or mention `$orbit-character-sprite` in the prompt.

## What gets copied

The installer copies only the portable skill payload:

- `SKILL.md`
- `README.md`
- `README.ru.md`
- `INSTALL.md`
- `AGENTS.md`
- `requirements.txt`
- `agents/`
- `assets/` when present
- `references/`
- `scripts/`

It intentionally excludes `.git`, `.github`, caches, `outputs/`, bytecode, logs, and temporary files. Yes, the installer refuses to carry local trash into Codex. Tiny miracle.
