# Orbit Character Sprite Skill

[English](README.md) | [Русский](README.ru.md)

`orbit-character-sprite` - это skill для Codex, который помогает создавать, проверять, ревьюить и упаковывать fixed-cell sprite sheets персонажей для OrbitSurvive.

Корень этого репозитория является корнем skill. Файл `SKILL.md` - главный файл, который AI-агент должен читать при использовании skill. Python-скрипты в `scripts/` - детерминированные помощники для pose guides, chroma-key cleanup, аудита sheet, review-артефактов и runtime packing.

## Для Чего Это

Используйте этот проект при работе с персонажной графикой OrbitSurvive:

- sprite sheets игрока, врагов, боссов и NPC
- four-direction walk cycles
- проверка fixed-cell sheet
- очистка chroma green
- contact sheets, silhouette sheets и GIF review packs
- Godot runtime sheets после явного approval арта

Skill специально строгий. Красивого still frame недостаточно. Персонаж проходит только тогда, когда отдельно проходят identity, motion, scale/cell, визуальная проверка и runtime packing.

## Структура Репозитория

```text
.
├── SKILL.md
├── README.md
├── README.ru.md
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
Основные инструкции skill. Агенты должны считать этот файл источником правды по workflow.

`agents/openai.yaml`:
UI metadata для списков skill в Codex/OpenAI.

`scripts/core/chroma.py`:
Единственный источник правды для распознавания и очистки chroma green. Не добавляйте вторую реализацию green-threshold в другом месте.

`scripts/build_pose_control_sheet.py`:
Создает pose-control sheets и GIF по направлениям. Это guides для генерации, не кандидатный арт.

`scripts/audit_walk_sheet.py`:
Жесткий gate для generated sheets. Проверяет fixed grid, visible bounds, edge clipping, height drift, head drift и foot baseline drift.

`scripts/build_approval_pack.py`:
Создает review-артефакты после успешного audit. Это нужно для human inspection, но не заменяет audit.

`scripts/pack_approved_walk_sheet.py`:
Упаковывает approved frame PNGs в runtime sheet. Скрипт может чистить, паддить, выравнивать и масштабировать, но не должен перерисовывать или скрывать плохую анимацию.

`scripts/selftest_pipeline.py`:
Синтетическая good/bad проверка пайплайна скриптов.

## Установка

Из чистого checkout:

```powershell
cd R:\Work\orbit-character-sprite-skill
python -m pip install pillow pytest
```

Скрипты написаны на обычном Python. Сейчас они зависят от Pillow; тесты используют pytest.

## Проверка

Запускайте это перед push:

```powershell
python C:\Users\retaw\.codex\skills\.system\skill-creator\scripts\quick_validate.py R:\Work\orbit-character-sprite-skill
python -m pytest scripts\tests
python scripts\selftest_pipeline.py
```

Ожидаемый результат:

- skill validation проходит
- все pytest tests проходят
- selftest печатает `SELFTEST PASS`

Selftest пишет временные файлы в `outputs/character_sprite/selftest`. Папка `outputs/` игнорируется git.

## Как GPT/Codex Агентам Работать Здесь

Когда агент работает с этим репозиторием:

1. Сначала прочитать `SKILL.md`.
2. Сохранять skill переносимым. Не хардкодить локальные пути вроде `R:\Work\OrbitSurvive`, если код явно не читает пользовательский checkout OrbitSurvive.
3. Не коммитить generated outputs, caches и локальные review artifacts.
4. Если поведение должно быть детерминированным, лучше улучшать скрипты, а не раздувать `SKILL.md` длинным текстом.
5. Держать `SKILL.md` сфокусированным на процедуре для агента. Human onboarding для GitHub держать в README.
6. После изменения chroma behavior запускать `python -m pytest scripts\tests` и проверять, что только `scripts/core/chroma.py` определяет `is_key_pixel`.
7. После изменения audit, pose или runtime packing запускать `python scripts\selftest_pipeline.py`.

Не заявляйте, что персонаж готов, только потому что прошел скрипт. Skill требует visual review и явного approval перед runtime export.

## Как Подключить Обратно В Codex

Клонировать репозиторий в папку skill с именем `orbit-character-sprite`:

```powershell
git clone https://github.com/RetawRDG/orbit-character-sprite-skill.git C:\Users\retaw\.codex\skills\orbit-character-sprite
```

Для repo-local использования в OrbitSurvive можно скопировать или клонировать сюда:

```powershell
R:\Work\OrbitSurvive\.agents\skills\orbit-character-sprite
```

После установки перезапустите или перезагрузите Codex session, чтобы список skill обновился.

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
3. Сгенерировать или получить candidate art.
4. Прогнать audit fixed-cell sheet.
5. Собрать review pack.
6. Попросить явный approval.
7. Упаковать runtime frames только после approval.

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
