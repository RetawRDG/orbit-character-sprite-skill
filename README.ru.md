# Orbit Character Sprite Skill

[English](README.md) | [Русский](README.ru.md)

`orbit-character-sprite` - это skill для Codex, который помогает создавать, проверять, ревьюить и упаковывать fixed-cell sprite sheets персонажей для OrbitSurvive.

Корень этого репозитория является корнем skill. Файл `SKILL.md` - главный файл, который AI-агент должен читать при использовании skill. Python-скрипты в `scripts/` - детерминированные помощники для pose guides, prompt packs, chroma-key cleanup, аудита sheet, first-success validation, review-артефактов и runtime packing.

## Быстрая Установка В Codex

Из чистого checkout:

```bash
python install.py --force --install-deps
```

Команда устанавливает skill сюда:

```text
$HOME/.agents/skills/orbit-character-sprite
```

Для repo-local установки в OrbitSurvive:

```powershell
python install.py --scope repo --repo-root R:\Work\OrbitSurvive --force --install-deps
```

Больше вариантов, включая one-line install с GitHub, описаны в [INSTALL.md](INSTALL.md).

## Для Чего Это

Используйте этот проект при работе с персонажной графикой OrbitSurvive:

- sprite sheets игрока, врагов, боссов и NPC
- four-direction walk cycles
- проверка fixed-cell sheet
- prompt packs для генерации из pose-control metadata
- очистка chroma green
- first-success playable artifact validation
- contact sheets, silhouette sheets и GIF review packs
- Godot runtime sheets после явного approval арта

Skill специально строгий. Красивого still frame недостаточно. Персонаж проходит только тогда, когда отдельно проходят identity, motion, scale/cell, визуальная проверка и runtime packing.

## Структура Репозитория

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
Основные инструкции skill. Агенты должны считать этот файл источником правды по workflow.

`AGENTS.md`:
Repo-level правила Codex для setup, scope control, validation и PR reporting.

`install.py` и `scripts/install_codex_skill.py`:
Устанавливают репозиторий в Codex skill scan locations как user skill или repo-local skill.

`agents/openai.yaml`:
UI metadata для списков skill в Codex/OpenAI.

`scripts/core/chroma.py`:
Единственный источник правды для распознавания и очистки chroma green. Не добавляйте вторую реализацию green-threshold в другом месте.

`scripts/build_pose_control_sheet.py`:
Создает pose-control sheets и GIF по направлениям. Это guides для генерации, не кандидатный арт.

`scripts/build_prompt_pack.py`:
Создает deterministic row-level `image_gen` prompts из pose-control metadata.

`scripts/audit_walk_sheet.py`:
Жесткий gate для generated sheets. Проверяет fixed grid, visible bounds, edge clipping, height drift, head drift и foot baseline drift.

`scripts/validate_sheet_contract.py`:
Preflight-проверка точных размеров sheet, row count, column count и expected cell size.

`scripts/build_approval_pack.py`:
Создает review-артефакты после успешного audit. Это нужно для human inspection, но не заменяет audit.

`scripts/pack_approved_walk_sheet.py`:
Упаковывает approved frame PNGs в runtime sheet. Скрипт может чистить, паддить, выравнивать и масштабировать, но не должен перерисовывать или скрывать плохую анимацию.

`scripts/validate_runtime_contract.py`:
Проверяет runtime frame size, frame count и required walk row keys против `player_visual.gd`.

`scripts/validate_first_success.py`:
Проверяет, что audit metrics, runtime manifest, runtime sheet и runtime GIF сходятся для первого playable handoff.

`scripts/selftest_pipeline.py`:
Синтетическая good/bad проверка пайплайна скриптов.

## Установка

Из чистого checkout:

```bash
python -m pip install -r requirements.txt
```

Скрипты написаны на обычном Python. Сейчас они зависят от Pillow; тесты используют pytest.

## Проверка

Запускайте это перед push:

```powershell
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Ожидаемый результат:

- skill validation проходит, если локальный skill creator validator доступен
- все pytest tests проходят
- selftest печатает `SELFTEST PASS`

Selftest пишет временные файлы в `outputs/character_sprite/selftest`. Папка `outputs/` игнорируется git.

## Как GPT/Codex Агентам Работать Здесь

Когда агент работает с этим репозиторием:

1. Сначала прочитать `AGENTS.md` и `SKILL.md`.
2. Сохранять skill переносимым. Не хардкодить локальные пути вроде `R:\Work\OrbitSurvive`, если код явно не читает пользовательский checkout OrbitSurvive.
3. Не коммитить generated outputs, caches и локальные review artifacts.
4. Если поведение должно быть детерминированным, лучше улучшать скрипты, а не раздувать `SKILL.md` длинным текстом.
5. Держать `SKILL.md` сфокусированным на процедуре для агента. Human GitHub onboarding держать в README, install детали - в `INSTALL.md`.
6. После изменения chroma behavior запускать `python -m pytest scripts\tests` и проверять, что только `scripts/core/chroma.py` определяет `is_key_pixel`.
7. После изменения audit, pose, prompt, first-success или runtime packing запускать `python scripts\selftest_pipeline.py`.

Не заявляйте, что персонаж готов, только потому что прошел скрипт. Skill требует visual review и явного approval перед runtime export.

## Типичный Workflow Для OrbitSurvive

Внутри checkout OrbitSurvive skill ожидает проектные файлы:

- `GAME_PLAN.md`
- `scripts/core/constants.gd`
- `scripts/entities/player_visual.gd`

Для работы над персонажем агент должен создавать output здесь:

```text
outputs/character_sprite/<character_id>_<YYYYMMDD_HHMM>_work/
```

Нормальный flow:

1. Записать `run_note.yml`.
2. Собрать pose-control assets.
3. Собрать prompt pack из pose metadata.
4. Сгенерировать или получить candidate art.
5. Проверить fixed-cell sheet contract.
6. Прогнать audit fixed-cell sheet.
7. Собрать review pack.
8. Попросить явный approval.
9. Упаковать runtime frames только после approval.
10. Проверить runtime contract и first-success artifacts.

## Правила Contribution На GitHub

Перед PR или прямым push:

```powershell
git status -sb
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Коммитьте только source files и намеренную metadata. Не коммитить:

- `outputs/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- локальные generated previews

Если изменение влияет на runtime assumptions OrbitSurvive, укажите ожидаемые consuming files в PR или commit message, особенно `scripts/entities/player_visual.gd`.
