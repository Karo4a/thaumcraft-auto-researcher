# Дизайн: GTNH-режим как модуль (edition) поверх ветки `original`

- **Дата**: 2026-10-04
- **Статус**: утверждён к реализации
- **Рабочая ветка**: `gtnh-edition` от `original` (`ee85682`)
- **Эталон GTNH-изменений**: ветка `master` (`b5d21a7`), не изменяется

## 1. Контекст

В репозитории две разошедшиеся ветки:

- `original` — свежий upstream (release 1.2.1 + sync). Содержит архитектурные улучшения:
  разбиение `Scenarios.py` на пакет `src/controllers/Scenarios/*`, потокобезопасный UI
  (`OverlayUI.safe*` через Qt-сигналы), `AppState` (чтение/хранение конфигов), переводы на
  11 языков, перенос конфигов в корневой `configs/`, импорты относительно `src/`.
- `master` — GTNH-форк на базе старого upstream (`4f99c38`). Содержит:
  - двухоконный инвентарь аспектов (`rectAspectsListingLT2/RB2`, `Aspect.rectAspectsNumber`);
  - удаление неиспользуемых в GTNH элементов UI (скролл страниц, кнопки микса, 5×5-сетку
    заменила 4×9, другие координаты окна);
  - оптимизацию `mixAspect`, confidence-фильтрацию предсказаний и разделение aspect/digit;
  - кнопку «Открыть все аспекты» и pause/resume в диалоге детекта;
  - данные аспекта `evolutio` и версию рецептов `"GTNH"`;
  - `main.py` в корне проекта.

Цель — получить результирующую ветку на основе `original`, в которой GTNH-функционал
оформлен изолированным модулем, а не правками общего кода. Это сохраняет возможность
регулярно подтягивать upstream и поддерживать оба режима одновременно.

## 2. Принятые решения

1. **База результата** — `original`; upstream-архитектура и потокобезопасность остаются в ядре.
2. **Два режима одновременно**: `vanilla` (поведение upstream 1:1) и `gtnh` (форк).
3. **Модуль GTNH** — `src/gtnh/`; ядро получает только явные точки расширения (editions).
4. **Все алгоритмические исправления** (mix optimization, confidence-фильтр, split
   aspect/digit) живут **только в модуле**; core `Neurolink`/`digit_recognition`/`mixAspect`
   не меняются.
5. **Выбор режима**: сценарий при первом запуске + флаг `--edition gtnh|vanilla` +
   хранение в appdata. В форке по умолчанию предлагается `gtnh`.
6. `master` не изменяется до конца работ — используется для сверки и отката.

## 3. Точки входа и импорт `configs` (Python 3.12)

### 3.1 Проблема

`src/main.py` использует плоские импорты `from controllers...` и `from configs...`.
Раскладка пакетов после upstream: `controllers` лежит в `src/`, а `configs` — в корне
репозитория.

- `python -m src.main` из корня: корень на `sys.path` (import `configs`), но `src`
  отсутствует (import `controllers` падает), если не выставлен `PYTHONPATH=src`.
- `python src/main.py` (в т.ч. кнопка Run в VS Code): `sys.path[0] = src/`
  (import `controllers`), корень не добавлен — `from configs...` падает. Именно поэтому в
  `master` пришлось вынести `main.py` в корень.

### 3.2 Решение

1. **Bootstrap в начале `src/main.py`** (первые исполняемые строки, до остальных импортов):
   добавить в `sys.path` и корень репозитория, и `src/`:
   ```python
   import os, sys
   _SRC_DIR = os.path.dirname(os.path.abspath(__file__))
   _ROOT_DIR = os.path.dirname(_SRC_DIR)
   for _p in (_ROOT_DIR, _SRC_DIR):
       if _p not in sys.path:
           sys.path.insert(0, _p)
   ```
   После этого работают все три способа: `python main.py`, `python -m src.main`,
   `python src/main.py`, а также кнопка VS Code. В замороженном (PyInstaller) виде пути
   либо уже присутствуют, либо вставка безвредна.

2. **Корневой `main.py` — тонкий шим** (совместимость со старыми ярлыками/привычкой GTNH):
   ```python
   import os, runpy
   runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'main.py'),
                  run_name='__main__')
   ```

3. **PyInstaller** (`pyinstaller_configs/autoPyToExe.json`): вход остаётся `./src/main.py`,
   `datas` дополняются `./src/gtnh/data;gtnh/data`; существующие
   `./configs/aspects_configs` и `./images` сохраняются. ВАЖНО: `configs/` — namespace-пакет
   без `__init__.py` в корне репозитория, поэтому для статического анализа импортов
   `pathex` должен включать и корень: значение `./src;./` (иначе `from configs...` не
   найдётся при сборке). Bootstrap из п. 1 на рантайме дополнительно добавляет корень.

4. **README**: зафиксировать три поддерживаемых способа запуска.

### 3.3 Окружение

Целевой интерпретатор — Python 3.12 (`py -3.12`). Устанавливаемые вручную зависимости
описываются только `requirements.txt` (PyQt5, pillow, appdata, keyboard, mouse, pyscreeze,
numpy, onnxruntime, auto-py-to-exe). Остальные пакеты из текущего `pip freeze`
(Eel, bottle, gevent, requests, sympy и т.п.) — транзитивные зависимости
`auto-py-to-exe`/`onnxruntime`, в `requirements.txt` их добавлять не нужно.

## 4. Архитектура

### 4.1 Точки расширения в ядре (минимальные правки `original`)

| Файл | Изменение |
|------|-----------|
| `src/editions/__init__.py` (новый) | Ленивый реестр: `getEditionNames()`, `selectEdition(name)`, `getEdition()`. Сопоставление id → модуль: `vanilla` → `editions.vanilla`, `gtnh` → `gtnh`. Модуль GTNH импортируется только в момент выбора. |
| `src/editions/vanilla.py` (новый) | `createEdition() -> BaseEdition` с поведением ядра (сценарии не переопределены, `createTI` — core, vanilla-конфиг контролов, без доп. рецептов). |
| `src/editions/base.py` (новый) | Контракт `BaseEdition`: `id`, `scenarioOverrides`, `createTI(...)`, `readThaumWindowControls()`, `saveThaumWindowControls(*args, **kwargs)`, `extraAspectRecipes()`, `extraAddonsRecipes()`. |
| `src/controllers/Scenarios/__init__.py` | Добавить `applyEdition(edition)`: подменяет атрибуты-сценарии из `edition.scenarioOverrides`. Межсценарные вызовы `Scenarios.x` подхватывают подмену автоматически. |
| `src/controllers/Scenarios/scenario00_Edition.py` (новый) | Сценарий `chooseEdition`: список `editions.getEditionNames()`, сохранение выбора, `selectEdition`, `applyEdition`, повторный `rereadAllConfigs`, переход к следующему сценарию. |
| `src/controllers/ThaumInteractor.py` | `createTI(...)` становится диспетчером: `getEdition().createTI(...)`; текущая реализация переименовывается в `_createTIDefault(...)`. |
| `src/utils/AppState.py` | `selectedEdition` + `EDITION_CONFIG_PATH` + `saveEdition()/rereadEdition()`; делегирование `rereadThaumWindowControls()`/`saveThaumWindowControls(*a, **k)` в `getEdition()`; в `rereadThaumVersion()` — merge `extraAspectRecipes()` в `allAspectRecipes` и `extraAddonsRecipes()` в `allAddonsRecipes`; валидация: если выбранная версия отсутствует в наборе — сброс в `None`. |
| `configs/constants.py` | `EDITION_CONFIG_PATH = to_appdata_path('user_configs/edition.json')`. |
| `configs/translations.py` | Новые ключи `TEXTS`: `chooseEdition`, `openAllAspects`; тексты во все 11 языков (EN-fallback). `programPaused` переиспользуется. |
| `src/controllers/Scenarios/__init__.py` экспорт | `scenario00_Edition` экспортируется наравне с остальными. |

Импортные циклы исключаются: `editions/__init__.py` не импортирует `controllers`/`gtnh`
на уровне модуля; `getEdition()` вызывается только во время выполнения, когда ядро уже
загружено.

### 4.2 Структура модуля `src/gtnh/`

```
src/gtnh/
  __init__.py        # GtnhEdition(BaseEdition) + createEdition(); регистрация id 'gtnh'
  constants.py       # RECT_ASPECTS_NUMBERS=2; слоты 4×9; DELAY_BETWEEN_EVENTS=0.05;
                     # DELAY_BETWEEN_RENDER=0.2; путь своего конфига контролов в appdata
  controls.py        # схема контролов GTNH: pointWritingMaterials, pointPapers,
                     # rectAspectsListingLT/RB, rectAspectsListingLT2/RB2,
                     # rectInventoryLT/RB, rectHexagonsCC, hexagonSlotSizeY
  aspect.py          # GtnhAspect(Aspect) + rectAspectsNumber
  interactor.py      # createTIGtnh(...), GtnhThaumInteractor(ThaumInteractor)
  recognition.py     # splitAspectsAndDigits, filterByMaxConfidence,
                     # aspects_count(aspects, digits)
  scenarios/
    __init__.py
    scenario3_ConfirmThaumWindowSlots.py   # GTNH-координаты и две зоны аспектов
    scenario7_DetectionAspectsDialogue.py  # два окна, openAllAspects, pause/resume
  data/
    aspects_configs/gtnhAspectsRecipes.json        # {"GTNH": {...}}
    aspects_configs/gtnhAddonsAspectsRecipes.json  # {"Twist Space Technology": {...}}
```

`GtnhEdition`:
`scenarioOverrides = {'confirmThaumWindowSlots': ..., 'detectionAspectsDialogue': ...}`,
`createTI = createTIGtnh`, `read/saveThaumWindowControls` из `gtnh/controls.py`,
`extraAspectRecipes`/`extraAddonsRecipes` читают JSON из `gtnh/data`.

`scenario6_DetectAspectsCreateTI` и `scenario8_Researchings` **не переопределяются**:
`scenario6` получает GTNH-интерактор через диспетчер `createTI`, `scenario8` работает с
ним полиморфно.

### 4.3 Порядок выбора режима

1. `main.py` парсит `--edition` (choices из `getEditionNames()`).
2. `AppState.rereadEdition()`; итоговый id = флаг → конфиг → иначе `None`.
3. Если `None` — `Scenarios.chooseEdition(UI)` и выход из `main`; сценарий после выбора
   сам вызывает `selectEdition` + `applyEdition` + `rereadAllConfigs` и продолжает цепочку.
4. Если id известен — `selectEdition(id)`, `applyEdition(edition)`, `rereadAllConfigs()`,
   далее существующая маршрутизация (`language → window controls → version → beReadyForCreatingTI`).
5. При смене режима выбор версии сбрасывается; конфиги контролов хранятся отдельно на
   каждый режим (vanilla — текущий файл, GTNH — `gtnhThaumControlsConfig.json`).

## 5. Функциональные группы

### A. Архитектура сценариев (разбиение из `original`)

1. Core-пакет `src/controllers/Scenarios/` и `shared.py` сохраняются без изменений по
   существу; добавляется только механизм подмены `applyEdition`.
2. GTNH-версии переносятся из `master:src/controllers/Scenarios.py`:
   - `confirmThaumWindowSlots` → `gtnh/scenarios/scenario3_ConfirmThaumWindowSlots.py`
     (координаты `topSlotsY`, `pointWritingMaterials`, `pointPapers`, второй
     `rectAspectsListing2`, `rectInventory`, `rectHexagonsCC/Ty`, сетка 4×9);
   - `detectionAspectsDialogue` → `gtnh/scenarios/scenario7_DetectionAspectsDialogue.py`
     (`drawAspects` по `RECT_ASPECTS_NUMBERS`, `onClickCell(..., rectAspectNumber)`, без
     scroll-кнопок, `switchToActiveState`/`switchToPausedState`, `openAllAspects`).
3. `openAllAspects` переносится в конец `scenario7` и регистрируется кнопкой.

### B. Двухоконный инвентарь

`GtnhThaumInteractor` переопределяет методы, отличающиеся в `master`:

- `__init__` — читает GTNH-схему контролов (без scroll/mix точек), создаёт
  `rectAspectsListingLT2/RB2`;
- `getRectAspectListingLTbyNumber` / `getRectAspectListingRBbyNumber`;
- `inventoryCellCoordsToPixelCoords(cellX, cellY, rectAspectNumber)`;
- `inventoryCellCoordsToPixelBoundingBox(cellX, cellY, rectAspectNumber)`;
- `takeAspectByCellCoords(cellX, cellY, rectAspectNumber)`;
- `getAspectByCellCoords(cellX, cellY, rectAspectNumber)`;
- `setAspectIntoAvailables(aspect, cellX, cellY, rectAspectNumber)`;
- `takeAspect(aspect)` — `mixAspect(aspect, 1)` + клик по сохранённым координатам;
- `fillByLinkMap(aspectsMap)` — без `scrollToLeftSide`/`currentAspectsPageIdx`;
- `updateAvailableAspectsInInventory(...)` — синхронный обход двух зон.

Не переопределяются и не используются в GTNH-пути (наследство core): `scrollLeft/Right`,
`scrollToLeftSide/RightSide`, `scrollToAspect`. Их вызовы из core-методов перекрыты
override-ами выше; это проверяется в верификации.

`GtnhAspect` добавляет `rectAspectsNumber`; `createTIGtnh` создаёт объекты
`GtnhAspect`. Core `Aspect` не меняется.

### C. UI GTNH

- В `gtnh/scenario3` отсутствуют точки скролла/микса; сохранение конфига идёт через
  `AppState.saveThaumWindowControls(...)` с GTNH-аргументами (делегируется в
  `gtnh/controls.py`).
- В `gtnh/scenario7`: кнопка «Открыть все аспекты», состояния active/paused по
  `Ctrl+Shift+Space` (текст `TEXTS.programPaused`), `activeStateDialogueObjects` включает
  кнопку.

### D. Потокобезопасность (перенос `safe*`-подхода из `original`)

1. Core-API `safe*` не меняется. Итоговый аудит UI-обращений GTNH-кода
   («место → поток → safe/обычный»):

| Место | Поток | Вызовы |
|---|---|---|
| `scenario7.switchToActiveState` / `switchToPausedState` / `togglePauseState` | keyboard hook | только `safeSetAllObjectsVisibility` / `safeSetObjectsVisibility`; хоткей регистрируется один раз стабильным toggle-callback. `safeSetKeyCallback` не используется: он реализован через `QTimer.singleShot`, который не срабатывает из потока keyboard |
| `scenario7.openAllAspects.mixAllAspects` | background thread | `TI.mixAspect` (мышиные события), `safeRemoveObject`, `UI.setTimeout(0, ...)` для возврата в GUI-поток; `try/except/finally` гарантирует восстановление UI |
| `scenario7.drawAspects` / `updateCurrentAspectData` / `switchToMainDialogue` / `switchToCellDialogue` | GUI-поток (mouse-callback) | обычные UI-вызовы, как в upstream `scenario7`; в `switchToCellDialogue` повторно регистрируется pause-хоткей |
| `scenario7.updateAvailableAspectsInInventory` | GUI-поток (из `directlyCreateTI` или `setTimeout`) | обычные `UI.repaint()` / `removeObject` (upstream-конвенция) |
| `interactor.mixAspect` → `_showDebugClick` | background thread | известное ограничение: при `PAINT_DEBUG=True` рисует отладочный круг напрямую из потока; по умолчанию `PAINT_DEBUG=False` |
| core `scenario8_Researchings` (не изменялся) | потоки/таймеры | `safe*` из `original` |

2. Mouse-callback-и (`onClickCell` и подобные) исполняются в GUI-потоке; в них допустимы
   обычные вызовы, как в upstream `scenario7`.
3. `updateAvailableAspectsInInventory` GTNH вызывается из GUI-потока (сценарий/mouse
   callback/`setTimeout`), поэтому его внутренние `UI.repaint()`/`removeObject`
   соответствуют upstream-конвенции.

### E. Алгоритмы (только модуль)

- `recognition.py` — перенос из `master`:
  `splitAspectsAndDigits`, `filterByMaxConfidence`, `aspects_count(aspects, digits)`.
- `GtnhThaumInteractor.updateAvailableAspectsInInventory` использует `recognition.*`
  вместо core `Neurolink.predict_inventory_aspects_count`; `aspect.count` берётся из
  предсказания напрямую (без `min` по страницам).
- `mixAspect(aspect, targetCount=3) -> bool` — итеративный расчёт дерева зависимостей и
  стоимости базовых аспектов, затем выполнение микса через drag/right-click; перенос из
  `6eb36de` с адаптацией под `GtnhAspect.rectAspectsNumber`.
- Core `src/logic/digit_recognition.py`, `src/logic/Neurolink.py` и core `mixAspect`
  остаются нетронутыми.

### F. Данные, конфиги, переводы

- Рецепты GTNH: `gtnh/data/aspects_configs/gtnhAspectsRecipes.json`,
  `gtnhAddonsAspectsRecipes.json`; подмешиваются в `AppState` через edition-хуки; vanilla
  их не видит.
- `images/color|mono/evolutio.png` кладутся в общий `images/` (аддитивно, core
  `getAspectImagePath` работает без правок).
- Свой файл контролов GTNH в appdata; vanilla-схема и файл не затрагиваются.
- Новые ключи `TEXTS` (`chooseEdition`, `openAllAspects`) + тексты для 11 языков;
  остальные тексты переиспользуются (`programPaused` и т.д.).
- `aspectsOrder.json` не меняется (изменения master в нём net-zero).
- `requirements.txt` уже синхронизирован с `original`.

### G. Запуск и сборка

- `src/main.py` — bootstrap путей + `argparse --edition` + выбор режима.
- Корневой `main.py` — шим через `runpy`.
- PyInstaller: datas модуля + существующие configs/images; entry `./src/main.py`.
- README: команды запуска и переключение режимов.

## 6. Маппинг изменений `master` → артефакты модуля

| Изменение в `master` | Куда переносится |
|---|---|
| `c258bd2`: `rectAspectsListingLT2/RB2`, `Aspect.rectAspectsNumber`, двухоконные координаты/сетка | `gtnh/interactor.py`, `gtnh/aspect.py`, `gtnh/constants.py`, `gtnh/controls.py` |
| `c258bd2`: удаление scroll-методов и `currentAspectsPageIdx` из GTNH-пути | `gtnh/interactor.py` (override, без вызова core scroll) |
| `c258bd2`: `aspects_count(aspects, digits)`, `splitAspectsAndDigits`, `filterByMaxConfidence` | `gtnh/recognition.py` |
| `c258bd2`: `saveThaumControlsConfig` с двумя rect и без scroll/mix | `gtnh/controls.py` (свой конфиг) |
| `c258bd2`: `confirmThaumWindowSlots` (координаты GTNH) | `gtnh/scenarios/scenario3_...` |
| `c258bd2`: `detectionAspectsDialogue` (два окна, без скролла) | `gtnh/scenarios/scenario7_...` |
| `6eb36de`: `openAllAspects` + active/paused | `gtnh/scenarios/scenario7_...` |
| `6eb36de`: оптимизированный `mixAspect`, `takeAspect` с `targetCount=1` | `gtnh/interactor.py` |
| `6eb36de`: аннотации типов в `LinksGeneration` | не переносим (нет поведения; upstream уже поправил) |
| `c258bd2`: `main.py` в корне | заменено на bootstrap + корневой шим (раздел 3) |
| `e9e216e`: `"GTNH"` в `aspectsRecipes.json`, `Twist Space Technology` в addons, `evolutio` images | `gtnh/data/...` + общие `images/` |
| `e216e96`/`e9655d4`: requirements | уже в `original` |
| `b5d21a7`: `.gitignore` | при необходимости перенести отдельные строки |

## 7. Этапы работ и коммиты

| # | Этап | Содержимое | DoD |
|---|------|-----------|-----|
| 0 | Подготовка | Сброс CRLF-шума, `.gitattributes`, ветка `gtnh-edition` от `original` | чистое дерево; ветка создана (сделано) |
| 1 | Каркас editions | `src/editions/*`, `applyEdition`, диспетчер `createTI`, `AppState` edition/merge/delegation, `scenario00_Edition`, переводы, `EDITION_CONFIG_PATH` | vanilla-прохождение не изменилось; `compileall` |
| 2 | Вход и пути | bootstrap в `src/main.py`, корневой `main.py`, `--edition`, README | все три способа запуска проходят импорт |
| 3 | Скелет модуля и данные | `src/gtnh/*` (constants, controls, aspect, data, `GtnhEdition`) | режим GTNH выбирается, данные подмешиваются |
| 4 | Интерактор и распознавание | двухоконность, `recognition`, `mixAspect`, thread-safety | модуль импортируется; проверки чистых функций |
| 5 | Сценарии GTNH | `gtnh/scenarios/scenario3`, `scenario7`, openAllAspects, pause | сценарии собираются и корректно wired |
| 6 | Упаковка и документация | PyInstaller datas, README, финальная сверка с `master` | конфиг сборки валиден; чек-листы пройдены |

Каждый этап — отдельный коммит; ядро и модуль коммитятся раздельно.

## 8. Верификация

1. **Python 3.12 / Windows**: `py -3.12 -m pip install -r requirements.txt`; проверка
   импортной стадии для `py -3.12 main.py`, `py -3.12 -m src.main`, `py -3.12 src\main.py`,
   VS Code Run.
2. **Vanilla-регресс**: полный проход сценариев в режиме `vanilla`; сравнение поведения с
   `original` (в первую очередь `scenario3/7/8`, thread-safe вызовы).
3. **GTNH**: ручной чек-лист — конфиг окна с двумя зонами, детект из обоих окон,
   confidence-фильтрация, open-all-aspects, pause/resume, микс аспектов, решение
   исследования; сверка с поведением `master`.
4. **Без игры**: `scripts_other/fake_aspects_inventory_generator` и
   `fake_researches_generator`; `unittest` для чистых функций (`recognition`, планирование
   `mixAspect` на stub-интеракторе) без новых зависимостей.
5. **Статика**: `python -m compileall src` после каждого этапа; ручная сверка импортов
   (плоский стиль) и отсутствия вызовов core-scroll в GTNH-пути.

## 9. Риски

- **Циклические импорты** при добавлении editions → ленивый реестр, `getEdition()` только
  в рантайме.
- **Несовпадение конфигов при смене режима** → раздельные файлы контролов, сброс версии
  при смене edition, валидация версии в `AppState`.
- **PyInstaller**: забытые datas `gtnh/data` → учтено в этапе 6.
- **Наследуемые core-методы**, ссылающиеся на scroll/страницы (`scroll*`, старый
  `fillByLinkMap`, `takeAspect`) → перекрыты; отдельный пункт проверки.
- **`GtnhAspect`**: совместимость `__repr__`/сравнения с core `Aspect` (строятся только
  модулем, используются в общих структурах) → проверяется на этапе 4.
- **Задержки/сетка GTNH**: модульный код обязан использовать `gtnh/constants.py`, иначе
  тайминги и координаты поедут.
- **Переводы**: новые ключи без текста у части языков → EN-fallback на этапе 1.

## 10. Вне scope

- Изменение нейросетевых моделей и логики inference за пределами `recognition.py`.
- Правки ветки `master`.
- Автоматическая миграция пользовательских конфигов из GTNH-формата `master` (кроме
  документирования).
- Рефакторинг core-сценариев, не требуемый для точек расширения.
