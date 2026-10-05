# GTNH Edition Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Интегрировать GTNH-функционал из ветки `master` в ветку на базе `original` как изолированный модуль (edition), сохранив оба режима (vanilla/GTNH), разбиение сценариев и потокобезопасный UI.

**Architecture:** Ядро получает минимальные точки расширения `src/editions/` (реестр + контракт `BaseEdition`), `AppState` делегирует чтение/сохранение конфигов активной edition. GTNH-функционал живёт в `src/gtnh/` и подключается через `Scenarios.applyEdition()`; алгоритмы и конфиги GTNH не затрагивают core-код.

**Tech Stack:** Python 3.12 (Windows `py -3.12`), PyQt5 5.15, Pillow, appdata, unittest (stdlib), PyInstaller/auto-py-to-exe.

**Спека:** `docs/superpowers/specs/2026-10-04-gtnh-edition-integration-design.md`

---

## Предусловия и соглашения

- Рабочая ветка: `gtnh-edition` (уже создана от `original`, HEAD `dbdfbd2`).
- Ветка `master` — только для сверки, не изменяется.
- **Порядок исполнения (важно):** Tasks 1, 2, 5, 3, 6, 7, 8, затем **Task 4** (точки входа) и Task 9. Task 4 подключает сценарий выбора режима к запуску приложения, поэтому его нельзя делать раньше Task 8 — иначе `--edition gtnh` упадёт до появления `gtnh/scenarios/`.
- Плоские импорты ядра: `from controllers...`, `from configs...`, `from utils...`, `from UI...`, `from logic...`. Модуль использует `from gtnh...`.
- Коммиты после каждого таска. Сообщения — в стиле репозитория (кратко, по-английски).
- Локальные тесты (WSL/Linux) выполняются в venv:
  ```bash
  python3 -m venv /tmp/opencode/taum-test-venv
  /tmp/opencode/taum-test-venv/bin/pip install appdata pillow
  ```
  Все команды тестов запускаются **из корня репозитория** (пути `configs/` и `images/` вычисляются от cwd).
- Тесты с GUI-импортами (PyQt5) в WSL пропускаются (`@unittest.skipUnless`); их прогоняет пользователь на Windows: `py -3.12 -m unittest discover -s tests -v`.

### Структура файлов (итог)

| Файл | Ответственность |
|---|---|
| `src/editions/__init__.py` | ленивый реестр edition: `getEditionNames`, `getEditionDisplayName`, `selectEdition`, `getEdition` |
| `src/editions/base.py` | контракт `BaseEdition` и vanilla-поведение по умолчанию |
| `src/editions/vanilla.py` | `VanillaEdition` |
| `src/controllers/Scenarios/scenario00_Edition.py` | первый запуск: выбор режима |
| `src/gtnh/__init__.py` | `GtnhEdition` + `createEdition` |
| `src/gtnh/constants.py` | GTNH-константы (2 зоны, 4×9, задержки) |
| `src/gtnh/controls.py` | чтение/запись GTNH-схемы контролов в appdata |
| `src/gtnh/aspect.py` | `GtnhAspect` с `rectAspectsNumber` |
| `src/gtnh/recognition.py` | split/filter/`aspects_count` (GTNH) |
| `src/gtnh/mixing.py` | чистое планирование микса (`planMixing`) |
| `src/gtnh/interactor.py` | `GtnhThaumInteractor` (двухоконность, микс, детект) |
| `src/gtnh/scenarios/scenario3_ConfirmThaumWindowSlots.py` | GTNH-координаты и 2 зоны |
| `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py` | 2 окна, openAllAspects, pause |
| `src/gtnh/data/aspects_configs/*.json` | рецепты `GTNH` и `Twist Space Technology` |
| `tests/*.py` | unittest-проверки чистых функций и конфигов |

---

## Task 1: Реестр editions (ядро)

**Files:**
- Create: `src/editions/base.py`
- Create: `src/editions/vanilla.py`
- Create: `src/editions/__init__.py`
- Test: `tests/test_editions.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_editions.py`:

```python
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
from editions.base import BaseEdition


class EditionsRegistryTest(unittest.TestCase):
    def tearDown(self):
        editions._currentEdition = None

    def test_vanilla_is_default(self):
        edition = editions.getEdition()
        self.assertEqual(edition.id, "vanilla")
        self.assertIsInstance(edition, BaseEdition)

    def test_select_vanilla(self):
        edition = editions.selectEdition("vanilla")
        self.assertEqual(edition.id, "vanilla")
        self.assertIs(editions.getEdition(), edition)

    def test_unknown_edition_raises(self):
        with self.assertRaises(ValueError):
            editions.selectEdition("no_such_edition")

    def test_base_edition_has_empty_extras(self):
        edition = BaseEdition()
        self.assertEqual(edition.scenarioOverrides, {})
        self.assertEqual(edition.extraAspectRecipes(), {})
        self.assertEqual(edition.extraAddonsRecipes(), {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_editions -v`
Expected: FAIL `ModuleNotFoundError: No module named 'editions'`

- [ ] **Step 3: Создать `src/editions/base.py`**

```python
from typing import Callable


class BaseEdition:
    id: str = "vanilla"
    displayName: str = "Thaumcraft"

    @property
    def scenarioOverrides(self) -> dict[str, Callable]:
        return {}

    def createTI(self, UI, noPointsConfigCallback, noSelectedVersionCallback):
        from controllers.ThaumInteractor import _createTIDefault
        return _createTIDefault(UI, noPointsConfigCallback, noSelectedVersionCallback)

    def readThaumWindowControls(self) -> dict | None:
        from configs.constants import THAUM_CONTROLS_CONFIG_PATH
        from utils.AppState import readJSONConfig
        return readJSONConfig(THAUM_CONTROLS_CONFIG_PATH)

    def saveThaumWindowControls(self, *args, **kwargs):
        from utils import AppState
        AppState._saveVanillaThaumWindowControls(*args, **kwargs)

    def extraAspectRecipes(self) -> dict:
        return {}

    def extraAddonsRecipes(self) -> dict:
        return {}
```

- [ ] **Step 4: Создать `src/editions/vanilla.py`**

```python
from editions.base import BaseEdition


class VanillaEdition(BaseEdition):
    id = "vanilla"
    displayName = "Thaumcraft"


def createEdition() -> BaseEdition:
    return VanillaEdition()
```

- [ ] **Step 5: Создать `src/editions/__init__.py`**

```python
import importlib
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from editions.base import BaseEdition

_EDITION_MODULES: dict[str, str] = {
    "vanilla": "editions.vanilla",
    "gtnh": "gtnh",
}

_currentEdition: "BaseEdition | None" = None


def getEditionNames() -> list[str]:
    return list(_EDITION_MODULES.keys())


def getEditionDisplayName(name: str) -> str:
    module = importlib.import_module(_EDITION_MODULES[name])
    return module.createEdition().displayName


def selectEdition(name: str) -> "BaseEdition":
    global _currentEdition
    if name not in _EDITION_MODULES:
        raise ValueError(f"Unknown edition: {name}")
    module = importlib.import_module(_EDITION_MODULES[name])
    _currentEdition = module.createEdition()
    logging.info(f"Edition selected: {name}")
    return _currentEdition


def getEdition() -> "BaseEdition":
    global _currentEdition
    if _currentEdition is None:
        selectEdition("vanilla")
    return _currentEdition
```

- [ ] **Step 6: Убедиться, что тест проходит**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_editions -v`
Expected: 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/editions tests/test_editions.py
git commit -m "feat: add editions registry core"
```

---

## Task 2: AppState: edition, делегирование контролов, merge рецептов

**Files:**
- Modify: `configs/constants.py` (добавить `EDITION_CONFIG_PATH`)
- Modify: `src/utils/AppState.py`
- Test: `tests/test_appstate.py`

- [ ] **Step 1: Написать падающий тест**

Создать `tests/test_appstate.py`:

```python
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
import utils.AppState as appstate_module
from editions.base import BaseEdition
from utils import AppState


class FakeEdition(BaseEdition):
    def extraAspectRecipes(self):
        return {"Test Edition": {"aer": [], "testaspect": ["aer", "ignis"]}}

    def extraAddonsRecipes(self):
        return {"Test Addon": {"testaddon": ["aer", "aqua"]}}


class AppStateEditionTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.versionPath = os.path.join(self.tmpdir.name, "version.json")
        with open(self.versionPath, "w", encoding="utf-8") as file:
            json.dump({"version": "Test Edition"}, file)
        self._origVersionPath = appstate_module.THAUM_VERSION_CONFIG_PATH
        appstate_module.THAUM_VERSION_CONFIG_PATH = self.versionPath

    def tearDown(self):
        appstate_module.THAUM_VERSION_CONFIG_PATH = self._origVersionPath
        editions._currentEdition = None
        self.tmpdir.cleanup()

    def test_edition_recipes_are_merged_and_selected(self):
        editions._currentEdition = FakeEdition()
        AppState.rereadThaumVersion()
        self.assertIn("Test Edition", AppState.allAspectRecipes)
        self.assertEqual(AppState.selectedThaumVersion, "Test Edition")
        self.assertIn("testaspect", AppState.aspectRecipes)
        self.assertIn("testaddon", AppState.aspectRecipes)

    def test_unknown_version_is_reset(self):
        # версия "Test Edition" есть только у FakeEdition, поэтому для vanilla она неизвестна
        AppState.rereadThaumVersion()
        self.assertIsNone(AppState.selectedThaumVersion)
        self.assertEqual(AppState.aspectRecipes, {})

    def test_edition_selection_roundtrip(self):
        path = os.path.join(self.tmpdir.name, "edition.json")
        self._origEditionPath = appstate_module.EDITION_CONFIG_PATH
        appstate_module.EDITION_CONFIG_PATH = path
        try:
            AppState.saveEdition("gtnh")
            self.assertEqual(AppState.selectedEdition, "gtnh")
            AppState.selectedEdition = None
            AppState.rereadEdition()
            self.assertEqual(AppState.selectedEdition, "gtnh")
        finally:
            appstate_module.EDITION_CONFIG_PATH = self._origEditionPath


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_appstate -v`
Expected: FAIL `AttributeError: module 'utils.AppState' has no attribute 'selectedEdition'` / `EDITION_CONFIG_PATH`

- [ ] **Step 3: Добавить `EDITION_CONFIG_PATH` в `configs/constants.py`**

Найти блок:

```python
THAUM_VERSION_CONFIG_PATH = to_appdata_path('user_configs/thaumVersionConfig.json')
THAUM_CONTROLS_CONFIG_PATH = to_appdata_path('user_configs/thaumControlsConfig.json')
LANGUAGE_CONFIG_PATH = to_appdata_path('user_configs/language.json')
```

Заменить на:

```python
THAUM_VERSION_CONFIG_PATH = to_appdata_path('user_configs/thaumVersionConfig.json')
THAUM_CONTROLS_CONFIG_PATH = to_appdata_path('user_configs/thaumControlsConfig.json')
LANGUAGE_CONFIG_PATH = to_appdata_path('user_configs/language.json')
EDITION_CONFIG_PATH = to_appdata_path('user_configs/edition.json')
```

- [ ] **Step 4: Правки `src/utils/AppState.py` — импорт и поле**

Заменить импорт:

```python
from configs.constants import LANGUAGE_CONFIG_PATH, THAUM_VERSION_CONFIG_PATH, THAUM_ASPECT_RECIPES_CONFIG_PATH, \
    THAUM_ADDONS_ASPECT_RECIPES_CONFIG_PATH, THAUM_CONTROLS_CONFIG_PATH, THAUM_ASPECTS_ORDER_CONFIG_PATH
```

на:

```python
from configs.constants import LANGUAGE_CONFIG_PATH, THAUM_VERSION_CONFIG_PATH, THAUM_ASPECT_RECIPES_CONFIG_PATH, \
    THAUM_ADDONS_ASPECT_RECIPES_CONFIG_PATH, THAUM_CONTROLS_CONFIG_PATH, THAUM_ASPECTS_ORDER_CONFIG_PATH, \
    EDITION_CONFIG_PATH
```

В `__init__` после строк:

```python
        self.selectedLanguage: None | str = None
        self.translatedTexts: dict[str, str] = {}
```

добавить:

```python

        self.selectedEdition: None | str = None
```

- [ ] **Step 5: Правки `AppState.py` — rereadEdition/saveEdition**

После метода `saveLanguage` (заканчивается строкой `logging.debug(f"Selected language successfully saved: {language}")` и вызовом `self.rereadLanguage()`) добавить:

```python
    # -------------------------
    def rereadEdition(self):
        readed = readJSONConfig(EDITION_CONFIG_PATH)
        if readed is None:
            self.selectedEdition = None
            return
        self.selectedEdition = readed.get('edition')
        logging.debug(f"Selected edition rereaded: {self.selectedEdition}")

    def saveEdition(self, edition: str):
        saveJSONConfig(EDITION_CONFIG_PATH, {
            'edition': edition,
        })
        logging.debug(f"Selected edition successfully saved: {edition}")
        self.rereadEdition()
```

- [ ] **Step 6: Правки `AppState.py` — `rereadThaumVersion`**

Заменить метод `rereadThaumVersion` целиком на:

```python
    def rereadThaumVersion(self):
        from editions import getEdition
        edition = getEdition()

        # get all recipes
        self.allAspectRecipes = readJSONConfig(THAUM_ASPECT_RECIPES_CONFIG_PATH) or {}
        self.allAspectRecipes |= edition.extraAspectRecipes()
        logging.debug(f"All aspects recipes rereaded")

        # get aspects order
        readed = readJSONConfig(THAUM_ASPECTS_ORDER_CONFIG_PATH)
        if readed is None:
            self.aspectsOrder = []
            logging.error(f'Cannot load recipes order config')
            return
        self.aspectsOrder = readed['aspects']
        logging.debug(f"Aspects order rereaded")

        # get selected version
        readed = readJSONConfig(THAUM_VERSION_CONFIG_PATH)
        if readed is None:
            self.selectedThaumVersion = None
            self.aspectRecipes = {}
            return
        self.selectedThaumVersion = readed['version']
        if self.selectedThaumVersion not in self.allAspectRecipes:
            logging.warning(f"Selected thaum version {self.selectedThaumVersion} is unknown for current edition. Resetting")
            self.selectedThaumVersion = None
            self.aspectRecipes = {}
            return
        logging.debug(f"Selected version rereaded: {self.selectedThaumVersion}")

        # get recipes FOR selected version
        self.aspectRecipes = self.allAspectRecipes.get(self.selectedThaumVersion)
        if self.aspectRecipes is None:
            logging.critical(f"No aspect recipes found for selected thaum version: {self.selectedThaumVersion}")
            self.aspectRecipes = {}
            return

        # add all recipes for addons
        self.allAddonsRecipes = readJSONConfig(THAUM_ADDONS_ASPECT_RECIPES_CONFIG_PATH) or {}
        self.allAddonsRecipes |= edition.extraAddonsRecipes()
        for addonRecipes in self.allAddonsRecipes.values():
            self.aspectRecipes |= addonRecipes
        logging.debug(f"Thaum version and aspects recipes successfully rereaded. Selected version: {self.selectedThaumVersion}")
```

- [ ] **Step 7: Правки `AppState.py` — делегирование конфига контролов**

Заменить

```python
    def rereadThaumWindowControls(self):
        self.thaumWindowControls = readJSONConfig(THAUM_CONTROLS_CONFIG_PATH)
        logging.debug(f"Thaum window controls rereaded")

    def saveThaumWindowControls(self, pointWritingMaterials, pointPapers, rectAspectsListingLT, rectAspectsListingRB,
                               pointAspectsScrollLeft, pointAspectsScrollRight,
                               pointAspectsMixLeft, pointAspectsMixCreate, pointAspectsMixRight, rectInventoryLT,
                               rectInventoryRB, rectHexagonsCC, hexagonSlotSizeY):
        saveJSONConfig(THAUM_CONTROLS_CONFIG_PATH, {
            "pointWritingMaterials": {"x": pointWritingMaterials.x, "y": pointWritingMaterials.y},
            "pointPapers": {"x": pointPapers.x, "y": pointPapers.y},
            "rectAspectsListingLT": {"x": rectAspectsListingLT.x, "y": rectAspectsListingLT.y},
            "rectAspectsListingRB": {"x": rectAspectsListingRB.x, "y": rectAspectsListingRB.y},
            "pointAspectsScrollLeft": {"x": pointAspectsScrollLeft.x, "y": pointAspectsScrollLeft.y},
            "pointAspectsScrollRight": {"x": pointAspectsScrollRight.x, "y": pointAspectsScrollRight.y},
            "pointAspectsMixLeft": {"x": pointAspectsMixLeft.x, "y": pointAspectsMixLeft.y},
            "pointAspectsMixCreate": {"x": pointAspectsMixCreate.x, "y": pointAspectsMixCreate.y},
            "pointAspectsMixRight": {"x": pointAspectsMixRight.x, "y": pointAspectsMixRight.y},
            "rectInventoryLT": {"x": rectInventoryLT.x, "y": rectInventoryLT.y},
            "rectInventoryRB": {"x": rectInventoryRB.x, "y": rectInventoryRB.y},
            "rectHexagonsCC": {"x": rectHexagonsCC.x, "y": rectHexagonsCC.y},
            "hexagonSlotSizeY": hexagonSlotSizeY,
        })
        logging.info(f"Thaum window controls config successfully saved: (long JSON ommitted)")
        self.rereadThaumWindowControls()
```

на:

```python
    def rereadThaumWindowControls(self):
        from editions import getEdition
        self.thaumWindowControls = getEdition().readThaumWindowControls()
        logging.debug(f"Thaum window controls rereaded")

    def saveThaumWindowControls(self, *args, **kwargs):
        from editions import getEdition
        getEdition().saveThaumWindowControls(*args, **kwargs)

    def _saveVanillaThaumWindowControls(self, pointWritingMaterials, pointPapers, rectAspectsListingLT, rectAspectsListingRB,
                                        pointAspectsScrollLeft, pointAspectsScrollRight,
                                        pointAspectsMixLeft, pointAspectsMixCreate, pointAspectsMixRight, rectInventoryLT,
                                        rectInventoryRB, rectHexagonsCC, hexagonSlotSizeY):
        saveJSONConfig(THAUM_CONTROLS_CONFIG_PATH, {
            "pointWritingMaterials": {"x": pointWritingMaterials.x, "y": pointWritingMaterials.y},
            "pointPapers": {"x": pointPapers.x, "y": pointPapers.y},
            "rectAspectsListingLT": {"x": rectAspectsListingLT.x, "y": rectAspectsListingLT.y},
            "rectAspectsListingRB": {"x": rectAspectsListingRB.x, "y": rectAspectsListingRB.y},
            "pointAspectsScrollLeft": {"x": pointAspectsScrollLeft.x, "y": pointAspectsScrollLeft.y},
            "pointAspectsScrollRight": {"x": pointAspectsScrollRight.x, "y": pointAspectsScrollRight.y},
            "pointAspectsMixLeft": {"x": pointAspectsMixLeft.x, "y": pointAspectsMixLeft.y},
            "pointAspectsMixCreate": {"x": pointAspectsMixCreate.x, "y": pointAspectsMixCreate.y},
            "pointAspectsMixRight": {"x": pointAspectsMixRight.x, "y": pointAspectsMixRight.y},
            "rectInventoryLT": {"x": rectInventoryLT.x, "y": rectInventoryLT.y},
            "rectInventoryRB": {"x": rectInventoryRB.x, "y": rectInventoryRB.y},
            "rectHexagonsCC": {"x": rectHexagonsCC.x, "y": rectHexagonsCC.y},
            "hexagonSlotSizeY": hexagonSlotSizeY,
        })
        logging.info(f"Thaum window controls config successfully saved: (long JSON ommitted)")
        self.rereadThaumWindowControls()
```

- [ ] **Step 7b: Обязательные дополнения (найдено code review)**

1. `rereadAllConfigs` должен вызывать `self.rereadEdition()`, иначе сохранённый режим не читается при старте:
   ```python
   def rereadAllConfigs(self):
       self.rereadLanguage()
       self.rereadEdition()
       self.rereadThaumVersion()
       self.rereadThaumWindowControls()
   ```
2. `rereadEdition` валидирует id: если `selectedEdition not in getEditionNames()` — сброс в `None` с warning.
3. В ветке сброса неизвестной версии в `rereadThaumVersion` также очищать `self.allAddonsRecipes = {}`.
4. Тесты: roundtrip через `rereadAllConfigs()` + новый `test_unknown_edition_is_reset`.

- [ ] **Step 8: Убедиться, что тесты проходят**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_appstate tests.test_editions -v`
Expected: все тесты PASS

- [ ] **Step 9: Commit**

```bash
git add configs/constants.py src/utils/AppState.py tests/test_appstate.py
git commit -m "feat(appstate): add edition state and delegate window controls"
```

---

## Task 3: Хуки editions в Scenarios, сценарий выбора режима, переводы

**Files:**
- Modify: `src/controllers/Scenarios/__init__.py`
- Create: `src/controllers/Scenarios/scenario00_Edition.py`
- Modify: `configs/translations.py`
- Test: `tests/test_translations.py`

- [ ] **Step 1: Написать падающий тест переводов**

Создать `tests/test_translations.py`:

```python
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.translations import TEXTS, TRANSLATIONS


def collectTextKeys() -> list[str]:
    keys = []
    for name, value in vars(TEXTS).items():
        if name.startswith("_") or name == "Buttons":
            continue
        if isinstance(value, str):
            keys.append(value)
    for name, value in vars(TEXTS.Buttons).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            keys.append(value)
    return keys


class TranslationsTest(unittest.TestCase):
    def test_all_languages_have_all_texts(self):
        keys = collectTextKeys()
        for language, texts in TRANSLATIONS.items():
            missing = [key for key in keys if key not in texts]
            self.assertEqual([], missing, f"{language} misses keys: {missing}")

    def test_new_edition_texts_are_translated(self):
        for language, texts in TRANSLATIONS.items():
            for key in (TEXTS.chooseEdition, TEXTS.openAllAspects):
                self.assertTrue(texts[key], f"{language} has empty {key}")
                self.assertNotEqual(texts[key], key, f"{language} did not translate {key}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_translations -v`
Expected: FAIL `AttributeError: type object 'TEXTS' has no attribute 'chooseEdition'`

- [ ] **Step 3: Добавить ключи в `TEXTS`**

В `configs/translations.py` после строки `donate = "donate"` добавить:

```python
    chooseEdition = "chooseEdition"
    openAllAspects = "openAllAspects"
```

- [ ] **Step 4: Добавить тексты в 11 языков**

Для каждого языка ниже найти пару строк `TEXTS.Buttons.donateGlobal: ...` + `TEXTS.Buttons.donateRussia: ...` и заменить её на ту же пару + пустую строку + два новых ключа. Русский язык:

```python
        TEXTS.Buttons.donateGlobal: "Скопировать ID крипто-кошелька",
        TEXTS.Buttons.donateRussia: "Сбор в Т-Банке",

        TEXTS.chooseEdition: "Выберите режим игры для автоматического исследователя:",
        TEXTS.openAllAspects: "Открыть все аспекты",
```

English (anchor `"Copy crypto wallet ID"` / `"Fundraiser in T-Bank"`):

```python
        TEXTS.chooseEdition: "Select the game edition for the auto researcher:",
        TEXTS.openAllAspects: "Open all aspects",
```

Italian (`"Copia ID portafoglio crypto"` / `"Raccolta fondi in T-Bank"`):

```python
        TEXTS.chooseEdition: "Seleziona l'edizione del gioco per il ricercatore automatico:",
        TEXTS.openAllAspects: "Apri tutti gli aspetti",
```

Dutch (`"Kopieer crypto wallet ID"` / `"Inzameling in T-Bank"`):

```python
        TEXTS.chooseEdition: "Selecteer de game-editie voor de automatische onderzoeker:",
        TEXTS.openAllAspects: "Alle aspecten openen",
```

Spanish (`"Copiar ID de billetera crypto"` / `"Colecta en T-Bank"`):

```python
        TEXTS.chooseEdition: "Selecciona la edición del juego para el investigador automático:",
        TEXTS.openAllAspects: "Abrir todos los aspectos",
```

Arabic (`"نسخ معرف المحفظة المشفرة"` / `"حملة جمع تبرعات في تي-بنك"`):

```python
        TEXTS.chooseEdition: "اختر إصدار اللعبة للباحث التلقائي:",
        TEXTS.openAllAspects: "فتح كل الخصائص",
```

Chinese (Traditional) (`"複製加密錢包ID"` / `"T-Bank募款"`):

```python
        TEXTS.chooseEdition: "選擇自動研究器要使用的遊戲版本：",
        TEXTS.openAllAspects: "開啟所有要素",
```

Chinese (Simplified) (`"复制加密钱包ID"` / `"T-Bank募款"`):

```python
        TEXTS.chooseEdition: "选择自动研究器使用的游戏版本：",
        TEXTS.openAllAspects: "打开所有要素",
```

French (`"Copier l'ID du portefeuille crypto"` / `"Collecte de fonds dans T-Bank"`):

```python
        TEXTS.chooseEdition: "Sélectionnez l'édition du jeu pour le chercheur automatique :",
        TEXTS.openAllAspects: "Ouvrir tous les aspects",
```

Hindi (`"क्रिप्टो वॉलेट आईडी कॉपी करें"` / `"टी-बैंक में धन संग्रह"`):

```python
        TEXTS.chooseEdition: "स्वचालित शोधकर्ता के लिए गेम संस्करण चुनें:",
        TEXTS.openAllAspects: "सभी पहलुओं को खोलें",
```

Korean (`"암호화폐 지갑 ID 복사"` / `"T-Bank 모금"`):

```python
        TEXTS.chooseEdition: "자동 연구원이 사용할 게임 에디션을 선택하세요:",
        TEXTS.openAllAspects: "모든 양상 열기",
```

- [ ] **Step 5: Убедиться, что тест переводов проходит**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_translations -v`
Expected: 2 tests PASS

- [ ] **Step 6: Переписать `src/controllers/Scenarios/__init__.py`**

Полное содержимое файла:

```python
from controllers.Scenarios.scenario00_Edition import chooseEdition
from controllers.Scenarios.scenario0_Language import chooseLanguage
from controllers.Scenarios.scenario1_Enroll import enroll
from controllers.Scenarios.scenario2_ConfigureThaumWindow import configureThaumWindowCoords
from controllers.Scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
from controllers.Scenarios.scenario4_ChooseThaumVersion import chooseThaumVersion
from controllers.Scenarios.scenario5_BeReadyForStartSolving import beReadyForStartSolving
from controllers.Scenarios.scenario6_DetectAspectsCreateTI import beReadyForCreatingTI
from controllers.Scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
from controllers.Scenarios.scenario8_Researchings import runResearching
from utils import AppState

# Снимок дефолтных реализаций ДО любых подмен (важно: getattr на момент импорта)
_DEFAULT_SCENARIOS = {
    "confirmThaumWindowSlots": confirmThaumWindowSlots,
    "detectionAspectsDialogue": detectionAspectsDialogue,
}


def applyEdition(edition):
    unknownScenarioNames = set(edition.scenarioOverrides) - set(_DEFAULT_SCENARIOS)
    if unknownScenarioNames:
        raise ValueError(f"Edition {edition.id} overrides unknown scenarios: {sorted(unknownScenarioNames)}")
    for scenarioName, scenarioFunction in _DEFAULT_SCENARIOS.items():
        globals()[scenarioName] = scenarioFunction
    for scenarioName, scenarioFunction in edition.scenarioOverrides.items():
        globals()[scenarioName] = scenarioFunction


def activateEdition(editionName: str):
    from editions import selectEdition
    edition = selectEdition(editionName)
    applyEdition(edition)
    AppState.rereadAllConfigs()
    return edition


def routeStartup(UI):
    if AppState.selectedLanguage is None:
        chooseLanguage(UI)
    elif AppState.thaumWindowControls is None:
        configureThaumWindowCoords(UI)
    elif AppState.selectedThaumVersion is None:
        chooseThaumVersion(UI)
    else:
        beReadyForCreatingTI(UI)
```

- [ ] **Step 7: Создать `src/controllers/Scenarios/scenario00_Edition.py`**

```python
import logging

from PyQt5.QtGui import QColor

from UI.OverlayUI import OverlayUI
from UI.primitives import Text
from configs.translations import TEXTS
from controllers import Scenarios
from controllers.Scenarios.shared import PointTextAnchor, createNextBackButtonsAndText
from configs.constants import MARGIN
from utils import AppState

DEFAULT_CHOOSE_EDITION_TEXT = "Select game edition / Выберите режим игры:"


def chooseEdition(UI: OverlayUI):
    import editions

    UI.clearAll()
    UI.createExitButton()

    def onSubmit():
        if selectedEdition[0] is None:
            logging.warning("Trying to go next but edition is not selected")
            return
        logging.info(f"Selected edition: {selectedEdition[0]}")
        AppState.saveEdition(selectedEdition[0])
        Scenarios.activateEdition(selectedEdition[0])
        Scenarios.routeStartup(UI)

    (infoText, nextButton, _) = createNextBackButtonsAndText(
        UI,
        AppState.translatedTexts.get(TEXTS.chooseEdition, DEFAULT_CHOOSE_EDITION_TEXT),
        onSubmit, [],
        None, [],
        "Go next >",
        None,
    )

    editionNames = editions.getEditionNames()
    editionDisplayNames = list(map(editions.getEditionDisplayName, editionNames))
    editionTextObjects = []

    selectedEditionObject: list[Text | None] = [None]
    selectedEdition: list[str | None] = [None]

    oldEditionKey = AppState.selectedEdition
    if oldEditionKey is None:
        oldEditionKey = "gtnh" if "gtnh" in editionNames else editionNames[0]
        logging.info(f"Selected edition in config is none. Selecting default: {oldEditionKey}")
    else:
        logging.info(f"Selected in config edition is: {oldEditionKey}")

    oldInfoTextCallback = infoText.onMoveCallback

    def updateTextsPosition():
        oldInfoTextCallback()
        startCurY = nextButton.y + nextButton.h + MARGIN * 2
        curY = startCurY
        curX = PointTextAnchor.x
        for i in range(len(editionTextObjects)):
            textObject = editionTextObjects[i]
            if curY > UI.height() - textObject.h:
                curX += 300
                curY = startCurY
            textObject.y = curY
            textObject.x = curX
            curY += textObject.h + MARGIN

    infoText.LT.onMoveCallback = updateTextsPosition
    infoText.onMoveCallback = updateTextsPosition
    startCurY = nextButton.y + nextButton.h + MARGIN * 2
    curY = startCurY
    curX = PointTextAnchor.x
    for i in range(len(editionNames)):
        editionKey = editionNames[i]
        editionName = editionDisplayNames[i]

        def onClickEdition(editionObject, editionKey):
            logging.debug(f"Click on edition {editionKey}")
            selectEdition(editionObject, editionKey)

        def selectEdition(editionObject, editionKey):
            if selectedEditionObject[0] is not None:
                selectedEditionObject[0].setColor(QColor('white'))
            logging.debug(f"Edition {editionKey} selected in UI. Previous selected edition is {selectedEdition[0]}")
            selectedEdition[0] = editionKey
            selectedEditionObject[0] = editionObject
            selectedEditionObject[0].setColor(QColor('purple'))

        editionObject = UI.addObject(Text(
            0, 0,
            editionName,
            color=QColor('white'),
            withBackground=True,
            padding=MARGIN,
            UI=UI,
            onClickCallback=onClickEdition,
            hoverable=True,
        ))
        if curY > UI.height() - editionObject.h:
            curX += 300
            curY = startCurY
        editionObject.x = curX
        editionObject.y = curY
        curY += editionObject.h + MARGIN
        editionObject.onClickCallbackArgs = [editionObject, editionKey]
        editionTextObjects.append(editionObject)
        if oldEditionKey == editionKey:
            selectEdition(editionObject, editionKey)

    logging.info(f"Selecting edition dialogue showed. Editions: {editionNames}")
```

- [ ] **Step 8: Проверка синтаксиса и тестов**

Run: `/tmp/opencode/taum-test-venv/bin/python -m compileall -q src configs && /tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_translations -v`
Expected: compileall без ошибок; тесты PASS

- [ ] **Step 9: Commit**

```bash
git add src/controllers/Scenarios/__init__.py src/controllers/Scenarios/scenario00_Edition.py configs/translations.py tests/test_translations.py
git commit -m "feat(scenarios): add edition selection scenario and edition hooks"
```

---

## Task 4: Точки входа (bootstrap путей, `--edition`, корневой шим, PyInstaller)

**Files:**
- Modify: `src/main.py`
- Create: `main.py` (корень)
- Modify: `pyinstaller_configs/autoPyToExe.json`

- [ ] **Step 1: Заменить `src/main.py` целиком**

```python
import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
for _path in (_ROOT_DIR, _SRC_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from controllers import Scenarios
from UI.OverlayUI import OverlayUI
from configs.constants import LOG_FILE_PATH, MAX_LOG_FILE_SIZE_BYTES, DEBUG, LOG_LEVEL, MAX_LOG_FILES_COUNT
from editions import getEditionNames
from utils import AppState
from utils.utils import createDirByFilePath

createDirByFilePath(LOG_FILE_PATH)
loggingHandlers = [logging.handlers.RotatingFileHandler(filename=LOG_FILE_PATH, maxBytes=MAX_LOG_FILE_SIZE_BYTES, backupCount=MAX_LOG_FILES_COUNT)]
if DEBUG:
    loggingHandlers.append(logging.StreamHandler(sys.stdout))  # output both to console and log-files
logging.basicConfig(
    handlers=loggingHandlers,
    format="%(asctime)s [%(levelname)s] (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s",
    level=LOG_LEVEL,
    force=True,
)

UI = OverlayUI(opacity=1)


def parseArgs():
    parser = argparse.ArgumentParser(description="Thaumcraft Auto Researcher")
    parser.add_argument("--edition", choices=getEditionNames(), default=None,
                        help="Game edition to use for this session (overrides saved config)")
    return parser.parse_args()


def main():
    args = parseArgs()
    AppState.rereadAllConfigs()

    try:
        editionName = args.edition or AppState.selectedEdition
        if editionName is None:
            Scenarios.chooseEdition(UI)
            return None

        Scenarios.activateEdition(editionName)
        Scenarios.routeStartup(UI)
        return None
    except Exception as e:
        logging.critical(f"Error excepted in main thread: {e}")
        return None


if __name__ == '__main__':
    logging.info("Program started")
    logging.info("###############")
    try:
        UI.start(main)
    except Exception as e:
        logging.critical(f"Error excepted in UI thread: {e}")
```

- [ ] **Step 2: Создать корневой `main.py` (шим совместимости)**

```python
import os
import runpy

if __name__ == '__main__':
    runpy.run_path(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'main.py'),
        run_name='__main__',
    )
```

- [ ] **Step 3: Проверить bootstrap путей (без PyQt)**

Run:
```bash
python3 -c "import runpy; runpy.run_path('src/main.py', run_name='not_main')" 2>&1 | tail -2
```
Expected: ошибка про `PyQt5`/`appdata` (любая), но **не** `No module named 'configs'` — значит `configs` резолвится. Проверить то же для `python3 src/main.py`:

```bash
python3 src/main.py 2>&1 | tail -2
```

- [ ] **Step 4: Обновить `pyinstaller_configs/autoPyToExe.json`**

Заменить:

```json
  {
   "optionDest": "datas",
   "value": "./configs/aspects_configs;configs/aspects_configs"
  },
```

на:

```json
  {
   "optionDest": "datas",
   "value": "./configs/aspects_configs;configs/aspects_configs"
  },
  {
   "optionDest": "datas",
   "value": "./src/gtnh/data;gtnh/data"
  },
```

и заменить:

```json
  {
   "optionDest": "pathex",
   "value": "./src"
  }
```

на:

```json
  {
   "optionDest": "pathex",
   "value": "./src;./"
  }
```

- [ ] **Step 5: Commit**

```bash
git add src/main.py main.py pyinstaller_configs/autoPyToExe.json
git commit -m "feat(entrypoint): bootstrap import paths and add edition CLI flag"
```

### Step 5b: Обязательные исправления (найдено code review Task 4)

1. PyInstaller не видит динамические импорты editions/gtnh — добавить в `pyinstaller_configs/autoPyToExe.json`:
   ```json
   { "optionDest": "hiddenimports", "value": "editions.vanilla" },
   { "optionDest": "hiddenimports", "value": "gtnh" }
   ```
2. `parseArgs()` перенести в `__main__` (главный поток) до `UI.start`; `SystemExit` → `sys.exit(error.code)`, прочие ошибки → critical + `sys.exit(2)`. Запуск: `UI.start(lambda: main(args))`.
3. В `main(args)` не делать полный `rereadAllConfigs()` заранее (иначе ложный warning о неизвестной версии для GTNH): сделать `rereadLanguage()` + `rereadEdition()`, а полный reread выполняет `activateEdition`. `AppState.selectedEdition = editionName` ставить ПОСЛЕ `activateEdition`.
4. Проверка бандла: собрать PyInstaller-архив и убедиться, что `editions.vanilla`, `gtnh.aspect`, `gtnh.interactor`, `gtnh.scenarios.scenario7_...` присутствуют.

---

## Task 5: Скелет модуля GTNH, конфиг контролов и данные

**Files:**
- Create: `src/gtnh/constants.py`
- Create: `src/gtnh/aspect.py`
- Create: `src/gtnh/controls.py`
- Create: `src/gtnh/__init__.py`
- Create: `src/gtnh/data/aspects_configs/gtnhAspectsRecipes.json`
- Create: `src/gtnh/data/aspects_configs/gtnhAddonsAspectsRecipes.json`
- Create: `images/color/evolutio.png`, `images/mono/evolutio.png`
- Test: `tests/test_gtnh_controls.py`, `tests/test_gtnh_edition.py`

- [ ] **Step 1: Написать падающий тест конфига контролов**

Создать `tests/test_gtnh_controls.py`:

```python
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.controls import readGtnhThaumWindowControls, saveGtnhThaumWindowControls


class GtnhControlsTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "gtnh_controls.json")
            point = lambda x, y: SimpleNamespace(x=x, y=y)
            saveGtnhThaumWindowControls(
                point(1, 2), point(3, 4),
                point(5, 6), point(7, 8),
                point(9, 10), point(11, 12),
                point(13, 14), point(15, 16), point(17, 18),
                19.0, path=path,
            )
            loaded = readGtnhThaumWindowControls(path=path)
            self.assertEqual(loaded["pointWritingMaterials"], {"x": 1, "y": 2})
            self.assertEqual(loaded["rectAspectsListingLT2"], {"x": 9, "y": 10})
            self.assertEqual(loaded["rectAspectsListingRB2"], {"x": 11, "y": 12})
            self.assertEqual(loaded["hexagonSlotSizeY"], 19.0)

    def test_missing_file_returns_none(self):
        self.assertIsNone(readGtnhThaumWindowControls(path="/no/such/file.json"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_controls -v`
Expected: FAIL `ModuleNotFoundError: No module named 'gtnh'`

- [ ] **Step 3: Создать `src/gtnh/constants.py`**

```python
RECT_ASPECTS_NUMBERS = 2

THAUM_ASPECTS_INVENTORY_SLOTS_X = 4
THAUM_ASPECTS_INVENTORY_SLOTS_Y = 9

DELAY_BETWEEN_EVENTS = 0.05  # seconds
DELAY_BETWEEN_RENDER = 0.2  # seconds
```

- [ ] **Step 4: Создать `src/gtnh/aspect.py`**

```python
from controllers.Aspect import Aspect


class GtnhAspect(Aspect):
    rectAspectsNumber: int | None

    def __init__(self, name: str, idx: int, cellX: int = None, cellY: int = None, rectAspectsNumber: int = None):
        super().__init__(name, idx, cellX, cellY)
        self.rectAspectsNumber = rectAspectsNumber
```

- [ ] **Step 5: Создать `src/gtnh/controls.py`**

```python
import logging

from configs.constants import to_appdata_path
from utils.AppState import readJSONConfig, saveJSONConfig

GTNH_THAUM_CONTROLS_CONFIG_PATH = to_appdata_path('user_configs/gtnhThaumControlsConfig.json')


def readGtnhThaumWindowControls(path: str = None) -> dict | None:
    return readJSONConfig(path or GTNH_THAUM_CONTROLS_CONFIG_PATH)


def saveGtnhThaumWindowControls(pointWritingMaterials, pointPapers,
                                rectAspectsListingLT, rectAspectsListingRB,
                                rectAspectsListingLT2, rectAspectsListingRB2,
                                rectInventoryLT, rectInventoryRB, rectHexagonsCC,
                                hexagonSlotSizeY, path: str = None):
    saveJSONConfig(path or GTNH_THAUM_CONTROLS_CONFIG_PATH, {
        "pointWritingMaterials": {"x": pointWritingMaterials.x, "y": pointWritingMaterials.y},
        "pointPapers": {"x": pointPapers.x, "y": pointPapers.y},
        "rectAspectsListingLT": {"x": rectAspectsListingLT.x, "y": rectAspectsListingLT.y},
        "rectAspectsListingRB": {"x": rectAspectsListingRB.x, "y": rectAspectsListingRB.y},
        "rectAspectsListingLT2": {"x": rectAspectsListingLT2.x, "y": rectAspectsListingLT2.y},
        "rectAspectsListingRB2": {"x": rectAspectsListingRB2.x, "y": rectAspectsListingRB2.y},
        "rectInventoryLT": {"x": rectInventoryLT.x, "y": rectInventoryLT.y},
        "rectInventoryRB": {"x": rectInventoryRB.x, "y": rectInventoryRB.y},
        "rectHexagonsCC": {"x": rectHexagonsCC.x, "y": rectHexagonsCC.y},
        "hexagonSlotSizeY": hexagonSlotSizeY,
    })
    logging.info("Thaum window controls config successfully saved (GTNH)")
```

- [ ] **Step 6: Создать `src/gtnh/__init__.py`**

```python
import json
import os
import sys

from editions.base import BaseEdition


def _dataPath(relativePath: str) -> str:
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'gtnh', 'data', relativePath)


def _loadJson(relativePath: str) -> dict:
    with open(_dataPath(relativePath), 'r', encoding='utf-8') as file:
        return json.load(file)


class GtnhEdition(BaseEdition):
    id = "gtnh"
    displayName = "GTNH"

    @property
    def scenarioOverrides(self) -> dict:
        from gtnh.scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
        from gtnh.scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
        return {
            "confirmThaumWindowSlots": confirmThaumWindowSlots,
            "detectionAspectsDialogue": detectionAspectsDialogue,
        }

    def createTI(self, UI, noPointsConfigCallback, noSelectedVersionCallback):
        from controllers.ThaumInteractor import _createTIDefault
        from gtnh.interactor import GtnhThaumInteractor
        return _createTIDefault(UI, noPointsConfigCallback, noSelectedVersionCallback,
                                interactorClass=GtnhThaumInteractor)

    def readThaumWindowControls(self):
        from gtnh.controls import readGtnhThaumWindowControls
        return readGtnhThaumWindowControls()

    def saveThaumWindowControls(self, *args, **kwargs):
        from gtnh.controls import saveGtnhThaumWindowControls
        from utils import AppState
        saveGtnhThaumWindowControls(*args, **kwargs)
        AppState.rereadThaumWindowControls()

    def extraAspectRecipes(self) -> dict:
        return _loadJson(os.path.join('aspects_configs', 'gtnhAspectsRecipes.json'))

    def extraAddonsRecipes(self) -> dict:
        return _loadJson(os.path.join('aspects_configs', 'gtnhAddonsAspectsRecipes.json'))


def createEdition():
    return GtnhEdition()
```

- [ ] **Step 7: Извлечь данные GTNH из `master`**

Run:

```bash
mkdir -p src/gtnh/data/aspects_configs
git show master:aspects_configs/aspectsRecipes.json | python3 -c "import json,sys; d=json.load(sys.stdin); json.dump({'GTNH': d['GTNH']}, open('src/gtnh/data/aspects_configs/gtnhAspectsRecipes.json','w'), indent=4, ensure_ascii=False)"
git show master:aspects_configs/addonsAspectsRecipes.json | python3 -c "import json,sys; d=json.load(sys.stdin); json.dump({'Twist Space Technology': d['Twist Space Technology']}, open('src/gtnh/data/aspects_configs/gtnhAddonsAspectsRecipes.json','w'), indent=4, ensure_ascii=False)"
python3 -c "import json; d=json.load(open('src/gtnh/data/aspects_configs/gtnhAspectsRecipes.json')); print(list(d.keys()), len(d['GTNH']))"
```

Expected: `['GTNH'] 48` (ключ GTNH и 48 аспектов).

- [ ] **Step 8: Скопировать картинки `evolutio`**

Run:

```bash
git show master:images/color/evolutio.png > images/color/evolutio.png
git show master:images/mono/evolutio.png > images/mono/evolutio.png
file images/color/evolutio.png images/mono/evolutio.png
```

Expected: `PNG image data` для обоих файлов.

- [ ] **Step 9: Добавить тест edition и прогнать тесты**

Создать `tests/test_gtnh_edition.py`:

```python
import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
# ВАЖНО: `import utils.AppState as X` даёт singleton из utils/__init__, а не модуль.
appstate_module = importlib.import_module("utils.AppState")
from editions.base import BaseEdition
from utils import AppState


class GtnhEditionTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.versionPath = os.path.join(self.tmpdir.name, "version.json")
        with open(self.versionPath, "w", encoding="utf-8") as file:
            json.dump({"version": "GTNH"}, file)
        self._origVersionPath = appstate_module.THAUM_VERSION_CONFIG_PATH
        appstate_module.THAUM_VERSION_CONFIG_PATH = self.versionPath

    def tearDown(self):
        appstate_module.THAUM_VERSION_CONFIG_PATH = self._origVersionPath
        editions._currentEdition = None
        self.tmpdir.cleanup()

    def test_select_gtnh(self):
        edition = editions.selectEdition("gtnh")
        self.assertEqual(edition.id, "gtnh")
        self.assertIsInstance(edition, BaseEdition)

    def test_extra_recipes_loaded(self):
        edition = editions.selectEdition("gtnh")
        self.assertIn("GTNH", edition.extraAspectRecipes())
        self.assertIn("Twist Space Technology", edition.extraAddonsRecipes())

    def test_appstate_merges_gtnh_recipes(self):
        editions.selectEdition("gtnh")
        AppState.rereadThaumVersion()
        self.assertEqual(AppState.selectedThaumVersion, "GTNH")
        self.assertIn("evolutio", AppState.aspectRecipes)
        self.assertIn("evolutio", AppState.allAddonsRecipes["Twist Space Technology"])


if __name__ == "__main__":
    unittest.main()
```

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v`
Expected: все тесты PASS

- [ ] **Step 10: Commit**

```bash
git add src/gtnh images/color/evolutio.png images/mono/evolutio.png tests/test_gtnh_controls.py tests/test_gtnh_edition.py
git commit -m "feat(gtnh): add edition skeleton, window controls config and data"
```

---

## Task 6: GTNH-распознавание и планирование микса (чистые функции)

**Files:**
- Create: `src/gtnh/recognition.py`
- Create: `src/gtnh/mixing.py`
- Test: `tests/test_gtnh_recognition.py`, `tests/test_gtnh_mixing.py`

- [ ] **Step 1: Написать падающие тесты**

`tests/test_gtnh_recognition.py`:

```python
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.recognition import aspects_count, filterByMaxConfidence, splitAspectsAndDigits


class Pred:
    def __init__(self, name, x, y, confidence=0.9, width=32, height=32):
        self.predictionName = name
        self.x = x
        self.y = y
        self.confidence = confidence
        self.width = width
        self.height = height


class RecognitionTest(unittest.TestCase):
    def test_split(self):
        preds = [Pred("ignis", 0, 0), Pred("4", 1, 1), Pred("aqua", 2, 2)]
        aspects, digits = splitAspectsAndDigits(preds)
        self.assertEqual([p.predictionName for p in aspects], ["ignis", "aqua"])
        self.assertEqual([p.predictionName for p in digits], ["4"])

    def test_filter_by_max_confidence(self):
        preds = [Pred("ignis", 0, 0, 0.5), Pred("ignis", 1, 1, 0.9), Pred("aqua", 2, 2, 0.3)]
        filtered = filterByMaxConfidence(preds)
        self.assertEqual(len(filtered), 2)
        ignis = next(p for p in filtered if p.predictionName == "ignis")
        self.assertEqual(ignis.confidence, 0.9)

    def test_aspects_count(self):
        aspect = Pred("ignis", 10, 10)
        digits = [Pred("1", 8, 10), Pred("2", 12, 10)]
        self.assertEqual(aspects_count([aspect], digits), {"ignis": 12})

    def test_aspects_count_ignores_digits_outside_aspect(self):
        aspect = Pred("ignis", 100, 100)
        digits = [Pred("7", 10, 10)]
        self.assertEqual(aspects_count([aspect], digits), {"ignis": 0})


if __name__ == "__main__":
    unittest.main()
```

`tests/test_gtnh_mixing.py`:

```python
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.mixing import planMixing


class FakeAspect:
    def __init__(self, name, count=0):
        self.name = name
        self.count = count
        self.cellX = 0
        self.cellY = 0
        self.rectAspectsNumber = 0


RECIPES = {
    "aer": [], "ignis": [], "aqua": [], "terra": [], "ordo": [], "perditio": [],
    "vacuos": ["aer", "perditio"],
    "potentia": ["ordo", "ignis"],
    "praecantatio": ["vacuos", "potentia"],
}


class MixingPlanTest(unittest.TestCase):
    def _makeAspects(self, counts=None):
        counts = counts or {}
        aspects = {}
        for name, recipe in RECIPES.items():
            default = 5 if len(recipe) == 0 else 0
            aspects[name] = FakeAspect(name, counts.get(name, default))
        return aspects

    def _plan(self, aspects, name, targetCount):
        return planMixing(aspects[name], targetCount,
                          lambda aspectName: aspects[aspectName],
                          lambda aspectName: RECIPES[aspectName])

    def test_builds_chain_bottom_up(self):
        aspects = self._makeAspects()
        plan = self._plan(aspects, "praecantatio", 1)
        self.assertEqual([aspect.name for aspect, _ in plan], ["potentia", "vacuos", "praecantatio"])

    def test_returns_none_when_basics_insufficient(self):
        aspects = self._makeAspects(counts={"ordo": 0, "ignis": 0})
        self.assertIsNone(self._plan(aspects, "praecantatio", 1))

    def test_returns_none_when_already_enough(self):
        aspects = self._makeAspects(counts={"praecantatio": 3})
        self.assertIsNone(self._plan(aspects, "praecantatio", 1))

    def test_returns_none_for_basic_without_count(self):
        aspects = self._makeAspects(counts={"aer": 0})
        self.assertIsNone(self._plan(aspects, "aer", 3))

    def test_simple_recipe_plan(self):
        aspects = self._makeAspects()
        plan = self._plan(aspects, "potentia", 1)
        self.assertEqual([aspect.name for aspect, _ in plan], ["potentia"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_recognition tests.test_gtnh_mixing -v`
Expected: FAIL `ModuleNotFoundError: No module named 'gtnh.recognition'`

- [ ] **Step 3: Создать `src/gtnh/recognition.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logic.onnx_inference import ObjectPrediction


def is_digit(prediction: "ObjectPrediction") -> bool:
    return prediction.predictionName in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]


def is_aspect(prediction: "ObjectPrediction") -> bool:
    return not is_digit(prediction)


def prediction_inside_prediction(pred_inner: Any, pred_outer: Any) -> bool:
    """True, если pred_inner находится внутри pred_outer"""
    x_min = pred_outer.x - pred_outer.width // 2
    x_max = pred_outer.x + pred_outer.width // 2
    y_min = pred_outer.y - pred_outer.height // 2
    y_max = pred_outer.y + pred_outer.height // 2
    return x_min <= pred_inner.x <= x_max and y_min <= pred_inner.y <= y_max


def remove_same_spot_predictions(digit_predictions: list) -> list:
    """
    Для случаев, когда на одну цифру приходится несколько предсказаний, расположенных примерно в одном месте.
    Убирает лишние предсказания, оставляя только самые уверенные
    """
    MIN_VALID_DIFF = 2.0
    prev_x = -666
    result = []
    digit_predictions.sort(key=lambda pred: pred.x)
    for digit_pred in digit_predictions:
        if abs(prev_x - digit_pred.x) < MIN_VALID_DIFF:
            if digit_pred.confidence > result[-1].confidence:
                result[-1] = digit_pred
        else:
            result.append(digit_pred)
            prev_x = digit_pred.x
    return result


def splitAspectsAndDigits(predictions: list) -> tuple[list, list]:
    aspects = []
    digits = []
    for prediction in predictions:
        if is_digit(prediction):
            digits.append(prediction)
        else:
            aspects.append(prediction)
    return aspects, digits


def filterByMaxConfidence(predictions: list) -> list:
    filteredAspects = {}
    for prediction in predictions:
        aspect = filteredAspects.get(prediction.predictionName)
        if aspect is None or prediction.confidence > aspect.confidence:
            filteredAspects[prediction.predictionName] = prediction
    return list(filteredAspects.values())


def group_aspects_and_digits(predictionsAspect: list, predictionsDigit: list) -> list[tuple]:
    result = []
    for aspect_pred in predictionsAspect:
        aspect_digits = []
        for digit_pred in predictionsDigit:
            if prediction_inside_prediction(digit_pred, aspect_pred):
                aspect_digits.append(digit_pred)
        result.append((aspect_pred, aspect_digits))
    return result


def aspects_count(predictionsAspect: list, predictionsDigit: list) -> dict[str, int]:
    counts = dict()
    for aspect_pred, aspect_digits_pred in group_aspects_and_digits(predictionsAspect, predictionsDigit):
        aspect_digits_pred = remove_same_spot_predictions(aspect_digits_pred)
        aspect_digits_pred.sort(key=lambda pred: pred.x)
        number = 0
        for digit_pred in aspect_digits_pred:
            number *= 10
            number += int(digit_pred.predictionName)
        counts[aspect_pred.predictionName] = number
    return counts
```

- [ ] **Step 4: Создать `src/gtnh/mixing.py`**

```python
from __future__ import annotations

import logging
from typing import Any, Callable, Optional


def planMixing(aspect: Any, targetCount: int,
               getAspectByName: Callable[[str], Any],
               getAspectRecipeByName: Callable[[str], list[str]]) -> Optional[list[tuple[Any, int]]]:
    """
    Строит план микса аспекта до targetCount снизу вверх (ингредиенты раньше результата).
    Возвращает список пар (аспект, количество миксов) или None, если микс невозможен.
    Повторяет алгоритм GTNH-ветки master.
    """
    if not aspect.count:
        aspect.count = 0
    if aspect.count >= targetCount:
        return None
    mixingTimes = targetCount - aspect.count
    logging.info(f"Planning mixing aspect {aspect} to {targetCount} for {mixingTimes} times...")
    recipe = getAspectRecipeByName(aspect.name)
    if len(recipe) < 2:  # Aspect is basic (Aqua, Terra, Aer, Ordo, Perditio)
        if aspect.count < mixingTimes:
            logging.critical(f"Ran out of basic aspect {aspect.name}")
        return None

    mixingStack = [aspect]
    totalMixingForAspect = {aspect.name: mixingTimes}
    totalCostBasicAspects = {}
    notProcessedRecipes = [recipe]

    while notProcessedRecipes:
        currentRecipe = notProcessedRecipes.pop()
        for aspectInRecipe in map(getAspectByName, currentRecipe):
            nextRecipe = getAspectRecipeByName(aspectInRecipe.name)
            if not aspectInRecipe.count:
                aspectInRecipe.count = 0
            mixingTimes = targetCount - aspectInRecipe.count
            if len(nextRecipe):  # Not basic aspect
                notProcessedRecipes.append(nextRecipe)
                mixingStack.append(aspectInRecipe)
                totalMixingForAspect[aspectInRecipe.name] = \
                    totalMixingForAspect.get(aspectInRecipe.name, 0) + mixingTimes
            else:
                totalCostBasicAspects[aspectInRecipe.name] = \
                    totalCostBasicAspects.get(aspectInRecipe.name, 0) + mixingTimes
                if totalCostBasicAspects[aspectInRecipe.name] > aspectInRecipe.count:
                    return None

    plan = []
    while mixingStack:
        aspectRecipe = mixingStack.pop()
        times = totalMixingForAspect[aspectRecipe.name]
        totalMixingForAspect[aspectRecipe.name] = 0
        if times > 0:
            plan.append((aspectRecipe, times))
    return plan
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_recognition tests.test_gtnh_mixing -v`
Expected: все тесты PASS

- [ ] **Step 6: Commit**

```bash
git add src/gtnh/recognition.py src/gtnh/mixing.py tests/test_gtnh_recognition.py tests/test_gtnh_mixing.py
git commit -m "feat(gtnh): add recognition and mixing planning helpers"
```

---

## Task 7: GTNH-интерактор и фабрика `createTI`

**Files:**
- Modify: `src/controllers/ThaumInteractor.py:20-55`
- Create: `src/gtnh/interactor.py`
- Test: `tests/test_gtnh_interactor.py`

- [ ] **Step 1: Написать падающий тест (PyQt-зависимый, с skip)**

Создать `tests/test_gtnh_interactor.py`:

```python
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

try:
    import gtnh.interactor as interactorModule
    from gtnh.interactor import GtnhThaumInteractor
    HAS_INTERACTOR = True
except Exception:
    HAS_INTERACTOR = False


class FakeAspect:
    def __init__(self, name, count=0):
        self.name = name
        self.count = count
        self.cellX = 0
        self.cellY = 0
        self.rectAspectsNumber = 0


RECIPES = {
    "aer": [], "ignis": [], "aqua": [], "terra": [], "ordo": [], "perditio": [],
    "vacuos": ["aer", "perditio"],
    "potentia": ["ordo", "ignis"],
    "praecantatio": ["vacuos", "potentia"],
}


def makeInteractor():
    interactorModule.eventsDelay = lambda: None
    ti = GtnhThaumInteractor.__new__(GtnhThaumInteractor)
    ti.recipes = RECIPES
    ti.allAspects = []
    ti.taken = []

    class FakePoint:
        def click(self, button=None):
            pass

        def release(self):
            pass

    def makeAspects():
        aspects = {}
        for name, recipe in RECIPES.items():
            aspects[name] = FakeAspect(name, 5 if len(recipe) == 0 else 0)
        ti.allAspects = list(aspects.values())
        return aspects

    ti.makeAspects = makeAspects
    ti.takeAspectByCellCoords = lambda cellX, cellY, rectAspectNumber: ti.taken.append((cellX, cellY, rectAspectNumber))
    ti.inventoryCellCoordsToPixelCoords = lambda cellX, cellY, rectAspectNumber: FakePoint()
    return ti


@unittest.skipUnless(HAS_INTERACTOR, "gtnh.interactor is not importable (PyQt5/PIL/onnxruntime missing)")
class GtnhInteractorMixTest(unittest.TestCase):
    def test_mix_chain_executes_bottom_up(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        result = ti.mixAspect(aspects["praecantatio"], 1)
        self.assertTrue(result)
        self.assertEqual(len(ti.taken), 3)
        self.assertEqual(aspects["praecantatio"].count, 1)
        self.assertEqual(aspects["vacuos"].count, 0)
        self.assertEqual(aspects["potentia"].count, 0)
        self.assertEqual(aspects["aer"].count, 4)
        self.assertEqual(aspects["perditio"].count, 4)
        self.assertEqual(aspects["ordo"].count, 4)
        self.assertEqual(aspects["ignis"].count, 4)

    def test_mix_returns_false_when_impossible(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["ordo"].count = 0
        aspects["ignis"].count = 0
        self.assertFalse(ti.mixAspect(aspects["praecantatio"], 1))

    def test_mix_aborts_when_ingredients_insufficient_during_execution(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["ordo"].count = 5
        aspects["ignis"].count = 0
        originalPlanMixing = interactorModule.planMixing
        interactorModule.planMixing = lambda *args, **kwargs: [(aspects["potentia"], 1)]
        try:
            self.assertFalse(ti.mixAspect(aspects["vacuos"], 1))
        finally:
            interactorModule.planMixing = originalPlanMixing
        self.assertEqual(ti.taken, [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Убедиться, что тест падает/скипается**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_interactor -v`
Expected: FAIL (нет `gtnh.interactor`) либо skipped в WSL без PyQt5

- [ ] **Step 3: Правка `src/controllers/ThaumInteractor.py` — фабрика**

Заменить существующий `createTI` (строки 20–55) на:

```python
def _createTIDefault(
        UI: OverlayUI,
        noPointsConfigCallback: Callable[[OverlayUI], None],
        noSelectedVersionCallback: Callable[[OverlayUI], None],
        interactorClass=None,
):
    if interactorClass is None:
        interactorClass = ThaumInteractor

    pointsConfig = AppState.thaumWindowControls
    if pointsConfig is None:
        noPointsConfigCallback(UI)
        return None

    selectedThaumVersion = AppState.selectedThaumVersion
    if selectedThaumVersion is None:
        noSelectedVersionCallback(UI)
        return None

    recipesConfig = AppState.aspectRecipes

    aspectsOrderConfig = AppState.aspectsOrder

    i = 0
    while i < len(aspectsOrderConfig):
        aspect = aspectsOrderConfig[i]
        if aspect not in recipesConfig:
            aspectsOrderConfig.remove(aspect)
        else:
            i += 1

    return interactorClass(UI, pointsConfig, recipesConfig, aspectsOrderConfig)


def createTI(
        UI: OverlayUI,
        noPointsConfigCallback: Callable[[OverlayUI], None],
        noSelectedVersionCallback: Callable[[OverlayUI], None],
):
    from editions import getEdition
    return getEdition().createTI(UI, noPointsConfigCallback, noSelectedVersionCallback)
```

- [ ] **Step 4: Создать `src/gtnh/interactor.py`**

```python
import logging
import math
import time
from typing import Callable

import pyscreeze  # for screenshot
from PIL import Image
from PyQt5.QtGui import QColor, QPixmap

from UI.OverlayUI import OverlayUI
from UI.primitives import Circle, Rect
from configs.constants import INVENTORY_SLOTS_X, INVENTORY_SLOTS_Y, ASPECTS_IMAGES_SIZE, \
    THAUM_HEXAGONS_SLOTS_COUNT, DEBUG, PAINT_DEBUG, UNKNOWN_ASPECT_IMAGE_PATH, \
    NEUROLINK_FREE_HEXAGON_PREDICTION_NAME, NEUROLINK_SCRIPT_IMAGE_PREDICTION_NAME, getAspectImagePath
from controllers.Aspect import Aspect
from controllers.Point import P
from controllers.ThaumInteractor import ThaumInteractor
from gtnh.aspect import GtnhAspect
from gtnh.constants import RECT_ASPECTS_NUMBERS, THAUM_ASPECTS_INVENTORY_SLOTS_X, \
    THAUM_ASPECTS_INVENTORY_SLOTS_Y, DELAY_BETWEEN_EVENTS, DELAY_BETWEEN_RENDER
from gtnh.mixing import planMixing
from gtnh.recognition import aspects_count, filterByMaxConfidence, splitAspectsAndDigits
from logic.Neurolink import Neurolink, ObjectPrediction


def eventsDelay():
    time.sleep(DELAY_BETWEEN_EVENTS)


def renderDelay():
    time.sleep(DELAY_BETWEEN_RENDER)


class GtnhThaumInteractor(ThaumInteractor):
    rectAspectsListingLT2: P
    rectAspectsListingRB2: P

    def __init__(self, UI: OverlayUI, controlsConfig: dict[str, dict[str, float]],
                 aspectsRecipes: dict[str, list[str, str]], orderedAvailableAspects: list[str]):
        self.UI = UI

        c = controlsConfig
        self.pointWritingMaterials = P(c['pointWritingMaterials']['x'], c['pointWritingMaterials']['y'])
        self.pointPapers = P(c['pointPapers']['x'], c['pointPapers']['y'])
        self.pointSafePosition = P((self.pointPapers.x + self.pointWritingMaterials.x) / 2, self.pointPapers.y)
        self.rectAspectsListingLT = P(c['rectAspectsListingLT']['x'], c['rectAspectsListingLT']['y'])
        self.rectAspectsListingRB = P(c['rectAspectsListingRB']['x'], c['rectAspectsListingRB']['y'])
        self.rectAspectsListingLT2 = P(c['rectAspectsListingLT2']['x'], c['rectAspectsListingLT2']['y'])
        self.rectAspectsListingRB2 = P(c['rectAspectsListingRB2']['x'], c['rectAspectsListingRB2']['y'])
        self.rectInventoryLT = P(c['rectInventoryLT']['x'], c['rectInventoryLT']['y'])
        self.rectInventoryRB = P(c['rectInventoryRB']['x'], c['rectInventoryRB']['y'])
        self.rectHexagonsCC = P(c['rectHexagonsCC']['x'], c['rectHexagonsCC']['y'])
        self.hexagonSlotSizeY = c['hexagonSlotSizeY']
        self.hexagonSlotSizeX = self.hexagonSlotSizeY * math.cos(math.pi / 6)
        self.increaseWorkingSlot()

        self.unknownAspectImage = self.loadImage(UNKNOWN_ASPECT_IMAGE_PATH)
        self.recipes = aspectsRecipes

        self.allAspects = [GtnhAspect(orderedAvailableAspects[i], i) for i in range(len(orderedAvailableAspects))]
        self.loadAspectsImages()

        logging.info(f"GTNH ThaumcraftInteractor successfully initialized")
        logging.info(f"All known aspects:     {self.allAspects}")
        logging.info(f"All available aspects: {self.availableAspects}")

    def getRectAspectListingLTbyNumber(self, rectAspectNumber: int) -> P:
        match rectAspectNumber:
            case 0:
                return self.rectAspectsListingLT
            case 1:
                return self.rectAspectsListingLT2
        raise ValueError(f"Unknown rectAspectNumber: {rectAspectNumber}")

    def getRectAspectListingRBbyNumber(self, rectAspectNumber: int) -> P:
        match rectAspectNumber:
            case 0:
                return self.rectAspectsListingRB
            case 1:
                return self.rectAspectsListingRB2
        raise ValueError(f"Unknown rectAspectNumber: {rectAspectNumber}")

    def inventoryCellCoordsToPixelCoords(self, cellX: int, cellY: int, rectAspectNumber: int) -> P:
        rectAspectsListingLT = self.getRectAspectListingLTbyNumber(rectAspectNumber)
        rectAspectsListingRB = self.getRectAspectListingRBbyNumber(rectAspectNumber)
        areaWidth = rectAspectsListingRB.x - rectAspectsListingLT.x
        areaHeight = rectAspectsListingRB.y - rectAspectsListingLT.y
        slotWidth = areaWidth / THAUM_ASPECTS_INVENTORY_SLOTS_X
        slotHeight = areaHeight / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        return P(
            rectAspectsListingLT.x + slotWidth * (cellX + 0.5),
            rectAspectsListingLT.y + slotHeight * (cellY + 0.5)
        )

    def inventoryCellCoordsToPixelBoundingBox(self, cellX: int, cellY: int, rectAspectNumber: int) -> tuple[float, float, float, float]:
        rectAspectsListingLT = self.getRectAspectListingLTbyNumber(rectAspectNumber)
        rectAspectsListingRB = self.getRectAspectListingRBbyNumber(rectAspectNumber)
        areaWidth = rectAspectsListingRB.x - rectAspectsListingLT.x
        areaHeight = rectAspectsListingRB.y - rectAspectsListingLT.y
        slotWidth = areaWidth / THAUM_ASPECTS_INVENTORY_SLOTS_X
        slotHeight = areaHeight / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        x = rectAspectsListingLT.x + slotWidth * cellX
        y = rectAspectsListingLT.y + slotHeight * cellY
        return x, y, x + slotWidth, y + slotHeight

    def takeAspectByCellCoords(self, cellX, cellY, rectAspectNumber):
        aspectPoint = self.inventoryCellCoordsToPixelCoords(cellX, cellY, rectAspectNumber)
        logging.info(f"Take aspect from cell ({cellX, cellY}), coordinates: {aspectPoint}")
        aspectPoint.hold()
        self._showDebugClick(aspectPoint, QColor('blue'))

    def getCellIdxByCellCoords(self, cellX: int, cellY: int) -> int:
        return cellX * THAUM_ASPECTS_INVENTORY_SLOTS_Y + cellY

    def getAspectByCellCoords(self, cellX: int, cellY: int, rectAspectNumber: int) -> Aspect | None:
        for aspect in self.availableAspects:
            if aspect.cellX == cellX and aspect.cellY == cellY and aspect.rectAspectsNumber == rectAspectNumber:
                return aspect
        return None

    def setAspectIntoAvailables(self, aspect: Aspect, cellX: int, cellY: int, rectAspectNumber: int):
        prevAspect = self.getAspectByCellCoords(cellX, cellY, rectAspectNumber)
        aspect.cellX = cellX
        aspect.cellY = cellY
        aspect.rectAspectsNumber = rectAspectNumber
        logging.info(f"Adding new aspect to availables: {aspect}. Previous aspect in this cell: {prevAspect}")

        if prevAspect is not None:
            if prevAspect == aspect:
                logging.info(f"Aspects is equal. Nothing to change")
                return
            aspectIdx = self.getAvailableAspectIdx(prevAspect)
            prevAspect.count = None
            prevAspect.cellX = None
            prevAspect.cellY = None
            prevAspect.rectAspectsNumber = None
            self.availableAspects[aspectIdx] = aspect
            logging.info(f"Aspect {prevAspect} successfully changed to {aspect} on idx {aspectIdx}")
        else:
            cellIdx = self.getCellIdxByCellCoords(cellX, cellY)
            cellsBeforeCount = 0
            for a in self.availableAspects:
                if self.getCellIdxByCellCoords(a.cellX, a.cellY) < cellIdx:
                    cellsBeforeCount += 1
            self.availableAspects.insert(cellsBeforeCount, aspect)
            logging.info(f"Aspect {aspect} successfully inserted on idx {cellsBeforeCount}")

        def removeAspectDuplicates():
            for a in self.availableAspects:
                if a.uid == aspect.uid and a.cellX != cellX and a.cellY != cellY:
                    self.availableAspects.remove(a)
                    removeAspectDuplicates()
                    break

        removeAspectDuplicates()

    def takeAspect(self, aspect: Aspect):
        self.mixAspect(aspect, 1)
        logging.info(f"Take aspect {aspect}...")
        self.takeAspectByCellCoords(aspect.cellX, aspect.cellY, aspect.rectAspectsNumber)
        aspect.count -= 1

    def mixAspect(self, aspect: Aspect, targetCount=3) -> bool:
        """
        Создаёт аспект миксом по рецепту (GTNH: drag/right-click).
        Возвращает True, если план выполнен, False — если микс невозможен.
        """
        plan = planMixing(aspect, targetCount, self.getAspectByName, self.getAspectRecipeByName)
        if plan is None:
            return False
        for aspectRecipe, mixingTimes in plan:
            aspect1, aspect2 = map(lambda name: self.getAspectByName(name),
                                   self.getAspectRecipeByName(aspectRecipe.name))
            # Защита от особенности planMixing: общий ингредиент может быть недосчитан
            if (aspect1.count or 0) < mixingTimes or (aspect2.count or 0) < mixingTimes:
                logging.critical(f"Not enough aspects to mix {aspectRecipe.name}: x{mixingTimes} of "
                                 f"{aspect1.name}({aspect1.count}) and {aspect2.name}({aspect2.count})")
                return False
            self.takeAspectByCellCoords(aspect1.cellX, aspect1.cellY, aspect1.rectAspectsNumber)
            aspect2_point = self.inventoryCellCoordsToPixelCoords(aspect2.cellX, aspect2.cellY, aspect2.rectAspectsNumber)
            eventsDelay()
            for _ in range(mixingTimes - 1):
                aspect2_point.click('right')
                eventsDelay()
            aspect2_point.release()
            eventsDelay()

            aspectRecipe.count += mixingTimes
            aspect1.count -= mixingTimes
            aspect2.count -= mixingTimes
        return True

    def fillByLinkMap(self, aspectsMap: dict[tuple[int, int], str]):
        logging.info(f"Filling aspects by link map: {aspectsMap}")

        aspectsListMap = list(aspectsMap.items())
        aspectsListMap.sort(key=lambda pair: self.getAspectByName(pair[1]).uid)
        logging.debug(f"Sorted aspects link map: {aspectsListMap}")

        for coords, aspectName in aspectsListMap:
            aspect = self.getAspectByName(aspectName)
            self.takeAspect(aspect)
            eventsDelay()
            self.putAspect(*coords)
            eventsDelay()

    def updateAvailableAspectsInInventory(self, onFinishCallback: Callable, callbackArgs=[]):
        logging.info("Detecting available aspects in inventory... (GTNH)")
        self.availableAspects = []

        debugHighlightingRect = self._addDebugHighlightingRect()
        slotWidth = (self.rectAspectsListingRB.x - self.rectAspectsListingLT.x) / THAUM_ASPECTS_INVENTORY_SLOTS_X
        slotHeight = (self.rectAspectsListingRB.y - self.rectAspectsListingLT.y) / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        self.UI.repaint()

        def detectAspects(screenshotImage: Image.Image, rectAspectsNumber: int):
            def exitWithSort():
                self.UI.removeObject(debugHighlightingRect)
                self.availableAspects.sort(key=lambda a: a.uid)
                logging.info("All detected available aspects was sorted")
                self.logAvailableAspects()
                onFinishCallback(*callbackArgs)

            logging.info("Wait for prediction aspects")
            predictions: list[ObjectPrediction] = Neurolink.predict_inventory_aspects(screenshotImage)
            predictionsAspect, predictionsDigit = splitAspectsAndDigits(predictions)
            predictionsAspect = filterByMaxConfidence(predictionsAspect)
            logging.info(f"Aspects predictions: {predictionsAspect}")

            logging.info("Wait for prediction counts")
            count_predictions = aspects_count(predictionsAspect, predictionsDigit)
            logging.info(f"Counts predictions:  {count_predictions}")

            for prediction in predictionsAspect:
                try:
                    aspect = self.getAspectByName(prediction.predictionName)
                    aspect_count = count_predictions[prediction.predictionName]
                except ValueError:
                    continue
                aspect.cellX = int(prediction.x // slotWidth)
                aspect.cellY = int(prediction.y // slotHeight)
                aspect.count = aspect_count or 0
                aspect.rectAspectsNumber = rectAspectsNumber
                logging.debug(f"Aspect: {aspect}, ({aspect.cellX}, {aspect.cellY}), rect: {rectAspectsNumber}")
                self.availableAspects.append(aspect)

            logging.info(f"All found aspects: {self.availableAspects}")
            exitWithSort()

        for rectAspectNumber, screenshotRBX, screenshotRBY, screenshotLTX, screenshotLTY \
                in zip(range(RECT_ASPECTS_NUMBERS),
                       (self.rectAspectsListingRB.x, self.rectAspectsListingRB2.x),
                       (self.rectAspectsListingRB.y, self.rectAspectsListingRB2.y),
                       (self.rectAspectsListingLT.x, self.rectAspectsListingLT2.x),
                       (self.rectAspectsListingLT.y, self.rectAspectsListingLT2.y)):
            screenshotImage = self.takeScreenshot(
                screenshotLTX, screenshotLTY,
                screenshotRBX, screenshotRBY,
                debugHighlightingRect
            )
            detectAspects(screenshotImage, rectAspectNumber)
```

Отличия от `master` (осознанные):
- `setAspectIntoAvailables` теперь выставляет `aspect.rectAspectsNumber` (в `master` был пропущен — ломало микс после ручной правки ячейки);
- `getCellIdxByCellCoords` переопределён (в core множитель 5, у GTNH — 9);
- локальные `splitAspectsAndDigits`/`filterByMaxConfidence` вынесены в `gtnh/recognition.py`;
- исправлены `rect: {rectAspectNumber}` → `rectAspectsNumber` в логе.

- [ ] **Step 4b: Обязательные исправления (найдено code review Task 7)**

1. `mixAspect`: если `(aspect.count or 0) >= targetCount` — вернуть `True` (already enough = успех).
2. `takeAspect`: при `mixAspect(aspect, 1) == False` залогировать critical и выйти без клика и без `count -= 1`.
3. `updateAvailableAspectsInInventory`: `exitWithSort()` вызывать один раз ПОСЛЕ обхода обеих зон; зоны задавать списком:
   ```python
   rects = [
       (self.rectAspectsListingLT, self.rectAspectsListingRB),
       (self.rectAspectsListingLT2, self.rectAspectsListingRB2),
   ]
   for rectAspectNumber, (rectLT, rectRB) in enumerate(rects):
       ...
       detectAspects(screenshotImage, rectAspectNumber)
   exitWithSort()
   ```
4. `slotWidth`/`slotHeight` считать внутри `detectAspects` по своему прямоугольнику.
5. Убрать неиспользуемые импорты (`pyscreeze`, `QPixmap`, `Circle`, `Rect`, `INVENTORY_SLOTS_*`, `ASPECTS_IMAGES_SIZE`, `THAUM_HEXAGONS_SLOTS_COUNT`, `DEBUG`, `PAINT_DEBUG`, `NEUROLINK_*`, `getAspectImagePath`, `RECT_ASPECTS_NUMBERS`, `DELAY_BETWEEN_RENDER`) и `renderDelay`.
6. Тесты: `test_mix_already_enough_returns_true`, `test_take_aspect_skips_when_cannot_mix`, `test_update_available_aspects_finishes_once`.
7. `mixAspect`: перед проверкой count проверять отсутствие координат у ингредиента:
   ```python
   if aspect1.cellX is None or aspect2.cellX is None:
       logging.critical(f"Cannot mix {aspectRecipe.name}: ingredient has no cell coords ...")
       return False
   ```
   Тест: `test_mix_aborts_when_ingredient_has_no_coords`.

- [ ] **Step 5: Прогнать тесты и синтаксис**

Run:
```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src && /tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v
```
Expected: compileall без ошибок; тесты PASS (или PyQt-тест skipped)

- [ ] **Step 6: Commit**

```bash
git add src/controllers/ThaumInteractor.py src/gtnh/interactor.py tests/test_gtnh_interactor.py
git commit -m "feat(gtnh): add two-window interactor and TI factory dispatch"
```

---

## Task 8: GTNH-сценарии (2 зоны, openAllAspects, pause)

**Files:**
- Create: `src/gtnh/scenarios/__init__.py`
- Create: `src/gtnh/scenarios/scenario3_ConfirmThaumWindowSlots.py`
- Create: `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py`

- [ ] **Step 1: Создать `src/gtnh/scenarios/__init__.py`**

```python
```
(пустой файл)

- [ ] **Step 2: Создать `src/gtnh/scenarios/scenario3_ConfirmThaumWindowSlots.py`**

Полное содержимое:

```python
import logging
from math import cos, pi, sin

from PyQt5.QtGui import QColor

from UI.primitives import Point, Line, Rect
from configs.constants import THAUM_HEXAGONS_SLOTS_COUNT
from configs.translations import TEXTS
from controllers import Scenarios
from controllers.Scenarios.shared import createNextBackButtonsAndText
from gtnh.constants import THAUM_ASPECTS_INVENTORY_SLOTS_X, THAUM_ASPECTS_INVENTORY_SLOTS_Y
from utils import AppState
from utils.LinkableValue import LinkableCoord, LinkableValue


def confirmThaumWindowSlots(UI, LTx, LTy, RBx, RBy):
    thaumWindowWidth = RBx - LTx
    thaumWindowHeight = RBy - LTy
    logging.info(
        f"Thaum window configured at: ({int(LTx)}, {int(LTy)}) x ({int(RBx)}, {int(RBy)}), width={thaumWindowWidth}, height={thaumWindowHeight}")

    UI.clearAll()
    UI.createExitButton()

    def saveControls():
        AppState.saveThaumWindowControls(
            pointWritingMaterials, pointPapers,
            rectAspectsListing.LT, rectAspectsListing.RB,
            rectAspectsListing2.LT, rectAspectsListing2.RB,
            rectInventory.LT, rectInventory.RB, rectHexagonsCC,
            (rectHexagonsCC.y - rectHexagonsTy) / (THAUM_HEXAGONS_SLOTS_COUNT // 2)
        )
        Scenarios.chooseThaumVersion(UI)

    createNextBackButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.confirmThaumWindowSlots],
        saveControls, [],
        Scenarios.configureThaumWindowCoords, [UI],
    )

    # Slots
    Ws = thaumWindowWidth / 15
    Hs = thaumWindowHeight / 10
    topSlotsY = LinkableValue(LTy + Hs * 0.7)  # GTNH
    pointWritingMaterials = UI.addObject(
        Point(LTx + Ws * 4.3, topSlotsY, movable=True, color=QColor('yellow')))  # writing materials
    pointPapers = UI.addObject(Point(LTx + Ws * 10.65, topSlotsY, movable=True, color=QColor('yellowgreen')))  # scrolls

    rectAspectsLT = LinkableCoord(LTx + Ws * 0.375, LTy + Hs * 0.375)
    rectAspectsRB = LinkableCoord(LTx + Ws * 3.3, LTy + Hs * 7.2)
    UI.addObject(
        Line(rectAspectsLT.x, rectAspectsLT.y, rectAspectsRB.x, rectAspectsRB.y, dashed=True, color=QColor('brown')))
    UI.addObject(
        Line(rectAspectsRB.x, rectAspectsLT.y, rectAspectsLT.x, rectAspectsRB.y, dashed=True, color=QColor('brown')))
    rectAspectsListing = UI.addObject(
        Rect(rectAspectsLT.x, rectAspectsLT.y, rectAspectsRB.x, rectAspectsRB.y, dashed=True, color=QColor('lime')))

    verticalListingLines = []
    for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
        xVal = rectAspectsLT.x + x * rectAspectsListing.w / THAUM_ASPECTS_INVENTORY_SLOTS_X
        line = Line(xVal, rectAspectsLT.y, xVal, rectAspectsRB.y, dashed=True, color=QColor('lime'), width=1)
        verticalListingLines.append(line)
        UI.addObject(line)
    horizontalListingLines = []
    for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
        yVal = rectAspectsLT.y + y * rectAspectsListing.h / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        line = Line(rectAspectsLT.x, yVal, rectAspectsRB.x, yVal, dashed=True, color=QColor('lime'), width=1)
        horizontalListingLines.append(line)
        UI.addObject(line)

    def updateListingRectCoords():
        rectW = rectAspectsRB.x - rectAspectsLT.x
        rectH = rectAspectsRB.y - rectAspectsLT.y
        for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
            xVal = rectAspectsLT.x + x * rectW / THAUM_ASPECTS_INVENTORY_SLOTS_X
            verticalListingLines[x - 1].S.x = xVal
            verticalListingLines[x - 1].E.x = xVal
        for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
            yVal = rectAspectsLT.y + y * rectH / THAUM_ASPECTS_INVENTORY_SLOTS_Y
            horizontalListingLines[y - 1].S.y = yVal
            horizontalListingLines[y - 1].E.y = yVal

    UI.addObject(Point(rectAspectsLT.x, rectAspectsLT.y, movable=True, onMoveCallback=updateListingRectCoords))
    UI.addObject(Point(rectAspectsRB.x, rectAspectsRB.y, movable=True,
                       onMoveCallback=updateListingRectCoords))  # aspects listing rectangle

    # v GTNH: second aspects listing zone v #
    rectAspectsLT2 = LinkableCoord(LTx + Ws * 11.75, LTy + Hs * 0.375)
    rectAspectsRB2 = LinkableCoord(LTx + Ws * 14.625, LTy + Hs * 7.2)
    UI.addObject(
        Line(rectAspectsLT2.x, rectAspectsLT2.y, rectAspectsRB2.x, rectAspectsRB2.y, dashed=True, color=QColor('brown')))
    UI.addObject(
        Line(rectAspectsRB2.x, rectAspectsLT2.y, rectAspectsLT2.x, rectAspectsRB2.y, dashed=True, color=QColor('brown')))
    rectAspectsListing2 = UI.addObject(
        Rect(rectAspectsLT2.x, rectAspectsLT2.y, rectAspectsRB2.x, rectAspectsRB2.y, dashed=True, color=QColor('orange')))

    verticalListingLines2 = []
    for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
        xVal = rectAspectsLT2.x + x * rectAspectsListing2.w / THAUM_ASPECTS_INVENTORY_SLOTS_X
        line = Line(xVal, rectAspectsLT2.y, xVal, rectAspectsRB2.y, dashed=True, color=QColor('orange'), width=1)
        verticalListingLines2.append(line)
        UI.addObject(line)
    horizontalListingLines2 = []
    for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
        yVal = rectAspectsLT2.y + y * rectAspectsListing2.h / THAUM_ASPECTS_INVENTORY_SLOTS_Y
        line = Line(rectAspectsLT2.x, yVal, rectAspectsRB2.x, yVal, dashed=True, color=QColor('orange'), width=1)
        horizontalListingLines2.append(line)
        UI.addObject(line)

    def updateListingRectCoords2():
        rectW = rectAspectsRB2.x - rectAspectsLT2.x
        rectH = rectAspectsRB2.y - rectAspectsLT2.y
        for x in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_X):
            xVal = rectAspectsLT2.x + x * rectW / THAUM_ASPECTS_INVENTORY_SLOTS_X
            verticalListingLines2[x - 1].S.x = xVal
            verticalListingLines2[x - 1].E.x = xVal
        for y in range(1, THAUM_ASPECTS_INVENTORY_SLOTS_Y):
            yVal = rectAspectsLT2.y + y * rectH / THAUM_ASPECTS_INVENTORY_SLOTS_Y
            horizontalListingLines2[y - 1].S.y = yVal
            horizontalListingLines2[y - 1].E.y = yVal

    UI.addObject(Point(rectAspectsLT2.x, rectAspectsLT2.y, movable=True, onMoveCallback=updateListingRectCoords2))
    UI.addObject(Point(rectAspectsRB2.x, rectAspectsRB2.y, movable=True,
                       onMoveCallback=updateListingRectCoords2))  # aspects listing rectangle 2
    # ^ GTNH ^ #

    rectLT = LinkableCoord(LTx + Ws * 3.6, LTy + Hs * 9.2)
    rectRB = LinkableCoord(LTx + Ws * 11.4, LTy + Hs * 11.8)
    UI.addObject(Line(rectLT.x, rectLT.y, rectRB.x, rectRB.y, dashed=True, color=QColor('brown')))
    UI.addObject(Line(rectRB.x, rectLT.y, rectLT.x, rectRB.y, dashed=True, color=QColor('brown')))
    rectInventory = UI.addObject(Rect(rectLT.x, rectLT.y, rectRB.x, rectRB.y, dashed=True, color=QColor('purple')))
    UI.addObject(Point(rectLT.x, rectLT.y, movable=True))
    UI.addObject(Point(rectRB.x, rectRB.y, movable=True))  # inventory rectangle

    rectHexagonsCC = LinkableCoord(LTx + Ws * 7.5, LTy + Hs * 5)  # GTNH
    rectHexagonsTy = LinkableValue(LTy + Hs * 2)  # GTNH
    verticalHexagonsLines = []
    deg30HexagonsLines = []
    deg60HexagonsLines = []
    for i in range(THAUM_HEXAGONS_SLOTS_COUNT):
        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        verticalHexagonsLines.append(line)
        UI.addObject(line)

        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        deg30HexagonsLines.append(line)
        UI.addObject(line)

        line = Line(0, 0, 0, 0, dashed=True, color=QColor('blue'), width=1)
        deg60HexagonsLines.append(line)
        UI.addObject(line)

    def updateHexagonsCoords():
        rad = rectHexagonsCC.y - rectHexagonsTy
        slotSizeY = rad / (THAUM_HEXAGONS_SLOTS_COUNT // 2)
        slotSizeX = slotSizeY * cos(pi / 6)
        for i in range(-THAUM_HEXAGONS_SLOTS_COUNT // 2, THAUM_HEXAGONS_SLOTS_COUNT // 2 + 1):
            idx = i + THAUM_HEXAGONS_SLOTS_COUNT // 2
            verticalHexagonsLines[idx].S.x = rectHexagonsCC.x + i * slotSizeX
            verticalHexagonsLines[idx].E.x = rectHexagonsCC.x + i * slotSizeX
            verticalHexagonsLines[idx].S.y = rectHexagonsCC.y - rad + abs(i) * slotSizeY / 2
            verticalHexagonsLines[idx].E.y = rectHexagonsCC.y + rad - abs(i) * slotSizeY / 2

            deg30HexagonsLines[idx].S.x = rectHexagonsCC.x + cos(pi / 6) * rad + (i < 0) * i * slotSizeX
            deg30HexagonsLines[idx].E.x = rectHexagonsCC.x - cos(pi / 6) * rad + (i > 0) * i * slotSizeX
            deg30HexagonsLines[idx].S.y = rectHexagonsCC.y + sin(pi / 6) * rad - (i < 0) * i * slotSizeY / 2 - (
                    i > 0) * i * slotSizeY
            deg30HexagonsLines[idx].E.y = rectHexagonsCC.y - sin(pi / 6) * rad - (i > 0) * i * slotSizeY / 2 - (
                    i < 0) * i * slotSizeY

            deg60HexagonsLines[idx].S.x = -deg30HexagonsLines[idx].S.x + rectHexagonsCC.x * 2
            deg60HexagonsLines[idx].E.x = -deg30HexagonsLines[idx].E.x + rectHexagonsCC.x * 2
            deg60HexagonsLines[idx].S.y = deg30HexagonsLines[idx].S.y
            deg60HexagonsLines[idx].E.y = deg30HexagonsLines[idx].E.y

    updateHexagonsCoords()

    UI.addObject(Point(rectHexagonsCC.x, rectHexagonsCC.y, movable=True,
                       onMoveCallback=updateHexagonsCoords))
    UI.addObject(Point(rectHexagonsCC.x, rectHexagonsTy, movable=True,
                       onMoveCallback=updateHexagonsCoords))  # hexagons rectangle
    logging.info("Configuring Thaum controls coordinates in window dialogue successfully showed")
```

- [ ] **Step 3: Скопировать scenario7 из ядра**

Run:

```bash
cp src/controllers/Scenarios/scenario7_DetectionAspectsDialogue.py src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py
```

- [ ] **Step 4: Правка импортов scenario7**

Заменить верхнюю часть файла:

```python
import logging

from PyQt5.QtGui import QColor

from UI.OverlayUI import KeyboardKeys
from UI.primitives import UIPrimitive, Image, Rect
from UI.primitives.Text import Align, Text
from configs.translations import TEXTS
from controllers.Aspect import Aspect
from controllers import Scenarios
from controllers.Scenarios.shared import createNextBackButtonsAndText, createButtonsAndText
from configs.constants import MARGIN, THAUM_ASPECTS_INVENTORY_SLOTS_X, THAUM_ASPECTS_INVENTORY_SLOTS_Y
from utils import AppState
from utils.utils import renderDelay
```

на:

```python
import logging
import threading

from PyQt5.QtGui import QColor

from UI.OverlayUI import KeyboardKeys
from UI.primitives import UIPrimitive, Image, Rect
from UI.primitives.Text import Text
from configs.translations import TEXTS
from controllers.Aspect import Aspect
from controllers import Scenarios
from controllers.Scenarios.shared import createNextBackButtonsAndText, createButtonsAndText
from configs.constants import MARGIN
from gtnh.constants import RECT_ASPECTS_NUMBERS, THAUM_ASPECTS_INVENTORY_SLOTS_X, THAUM_ASPECTS_INVENTORY_SLOTS_Y
from utils import AppState
```

- [ ] **Step 5: Правка начала `detectionAspectsDialogue`**

Заменить:

```python
def detectionAspectsDialogue(UI, TI):
    TI.scrollToLeftSide()
    logging.info(f"TI successfully detected all aspects")
```

на:

```python
def detectionAspectsDialogue(UI, TI):
    logging.info(f"TI successfully detected all aspects")
```

- [ ] **Step 6: Добавить кнопку openAllAspects и pause-состояния**

После строки `cellsObjects = []` (перед `def updateCurrentAspectData():`) вставить:

```python
    openAllAspectsButton = Text(
        20,
        260,
        AppState.translatedTexts[TEXTS.openAllAspects],
        color=QColor('white'),
        withBackground=True,
        padding=MARGIN,
        UI=UI,
        hoverable=True,
        clickable=True,
        onClickCallback=openAllAspects,
        onClickCallbackArgs=[UI, TI],
    )
    UI.addObject(openAllAspectsButton)

    onPausedText = UI.addObject(Text(
        MARGIN, MARGIN,
        AppState.translatedTexts[TEXTS.programPaused],
        color=QColor('white'),
        withBackground=True,
        padding=MARGIN,
        movable=True,
        UI=UI,
    ))
    onPausedText.setVisibility(False)
    pausedStateDialogueObjects = [onPausedText]
    activeStateDialogueObjects = [mainText, nextButton, backButton, openAllAspectsButton]

    def switchToActiveState():
        logging.info("Switching to active state")
        UI.safeClearKeyCallbacks()
        UI.safeSetKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], switchToPausedState)
        UI.safeSetAllObjectsVisibility(False)
        UI.safeSetObjectsVisibility(activeStateDialogueObjects, True)
        UI.safeSetObjectsVisibility(cellsObjects, True)
        exitButton.setVisibility(True)

    def switchToPausedState():
        logging.info("Switching to paused state")
        UI.safeClearKeyCallbacks()
        UI.safeSetKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], switchToActiveState)
        UI.safeSetAllObjectsVisibility(False)
        UI.safeSetObjectsVisibility(pausedStateDialogueObjects, True)

    UI.setKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], switchToPausedState)
```

- [ ] **Step 7: Заменить `drawCurrentPageAspects` на двухоконный `drawAspects`**

Заменить функцию `drawCurrentPageAspects` целиком (от `def drawCurrentPageAspects():` до строки `drawCurrentPageAspects()` включительно) на:

```python
    def drawAspects():
        UI.removeObjects(cellsObjects)
        cellsObjects.clear()

        def onClickCell(aspect: Aspect, cellX: int, cellY: int, rectAspectNumber: int):
            logging.info(f"Click on aspect to change: {aspect}, cellX: {cellX}, cellY {cellY}, rect: {rectAspectNumber}")
            currentAspectCellCoords[0] = cellX
            currentAspectCellCoords[1] = cellY
            currentAspectCellCoords[2] = rectAspectNumber
            currentAspectCount[0] = str(aspect.count if aspect else "")
            currentAspect[0] = aspect
            updateCurrentAspectData()
            switchToCellDialogue()

        for rectAspectNumber in range(RECT_ASPECTS_NUMBERS):
            for cellX in range(THAUM_ASPECTS_INVENTORY_SLOTS_X):
                for cellY in range(THAUM_ASPECTS_INVENTORY_SLOTS_Y):
                    aspect = TI.getAspectByCellCoords(cellX, cellY, rectAspectNumber)
                    cellRectCoords = list(TI.inventoryCellCoordsToPixelBoundingBox(cellX, cellY, rectAspectNumber))
                    cellWidth = cellRectCoords[2] - cellRectCoords[0]
                    cellHeight = cellRectCoords[3] - cellRectCoords[1]
                    cellRect = Rect(
                        *cellRectCoords,
                        color=cellColorFree,
                        fill=QColor(cellColorFree),
                        fillOpacity=0.1,
                        onClickCallback=onClickCell,
                        onClickCallbackArgs=[aspect, cellX, cellY, rectAspectNumber],
                        hoverable=True,
                        clickable=True,
                    )
                    imageSize = cellHeight / 3 * 2
                    imageRect = Rect(
                        cellRectCoords[0], cellRectCoords[1],
                        cellRectCoords[2], cellRectCoords[1] + imageSize,
                        color=QColor('transparent'),
                        fill=QColor(cellColorFree),
                        fillOpacity=0.7,
                        hoverable=True,
                        clickable=True,
                    )
                    cellAspectImageObject = Image(
                        cellRectCoords[0] + imageSize / 2,
                        cellRectCoords[1] - imageSize / 2,
                        imageSize,
                        imageSize,
                        None,
                    )
                    cellsObjects.append(cellRect)
                    cellsObjects.append(imageRect)
                    cellsObjects.append(cellAspectImageObject)
                    UI.addObject(cellRect)
                    UI.addObject(imageRect)
                    UI.addObject(cellAspectImageObject)

                    if aspect:
                        cellAspectImageObject.setImage(aspect.pixMapImage)
                        cellAspectImageCountText = Text(
                            cellRectCoords[0] + cellWidth * 0.4,
                            cellRectCoords[1] + cellHeight * 0.2,
                            str(aspect.count),
                            color=QColor('#ff4444'),
                            withBackground=True,
                            padding=0,
                        )
                        cellsObjects.append(cellAspectImageCountText)
                        UI.addObject(cellAspectImageCountText)

        logging.info(f"Inventory aspects successfully drawn (2 zones)")
    drawAspects()
```

- [ ] **Step 8: Убрать блок scroll-кнопок**

Удалить блок от строки `LPoint = TI.pointAspectsScrollLeft` до строки `mainDialogueObjects = [mainText, nextButton, backButton, buttonScrollL, buttonScrollR]` включительно и заменить его на:

```python
    mainDialogueObjects = [mainText, nextButton, backButton, openAllAspectsButton]
```

- [ ] **Step 9: Обновить координаты текущей ячейки**

Заменить:

```python
    currentAspectCellCoords: list[int | None] = [None, None]
```

на:

```python
    currentAspectCellCoords: list[int | None] = [None, None, None]
```

- [ ] **Step 10: Обновить `confirmAspectChanges`**

Заменить:

```python
        TI.setAspectIntoAvailables(
            newAspect,
            currentAspectCellCoords[0], currentAspectCellCoords[1]
        )
```

на:

```python
        TI.setAspectIntoAvailables(newAspect, *currentAspectCellCoords)
```

- [ ] **Step 11: Обновить `switchToMainDialogue`**

Заменить:

```python
    def switchToMainDialogue():
        logging.info(f"Switching to a main change inventory apsects dialogue...")
        UI.setObjectsVisibility(cellDialogueObjects, False)
        UI.setObjectsVisibility(mainDialogueObjects, True)
        buttonScrollL.setVisibility(True)
        buttonScrollR.setVisibility(True)
        if TI.currentAspectsPageIdx <= 0:
            buttonScrollL.setVisibility(False)
        if TI.currentAspectsPageIdx >= TI.maxAspectsPagesCount - 1:
            buttonScrollR.setVisibility(False)
        drawCurrentPageAspects()
```

на:

```python
    def switchToMainDialogue():
        logging.info(f"Switching to a main change inventory apsects dialogue...")
        UI.setObjectsVisibility(cellDialogueObjects, False)
        UI.setObjectsVisibility(mainDialogueObjects, True)
        drawAspects()
```

- [ ] **Step 12: Добавить `openAllAspects` в конец файла**

```python
def openAllAspects(UI, TI):
    logging.info("Opening all aspects (GTNH)")
    UI.clearAll()
    UI.repaint()
    UI.createExitButton()
    onProcessText = Text(
        MARGIN, MARGIN,
        AppState.translatedTexts[TEXTS.openAllAspects] + "...",
        color=QColor('white'),
        withBackground=True,
        padding=MARGIN,
        UI=UI,
    )
    UI.addObject(onProcessText)

    def mixAllAspects():
        setAvailableAspectNames = set(map(lambda aspect: aspect.name, TI.availableAspects))
        for result in TI.allAspects:
            recipe = TI.getAspectRecipeByName(result.name)
            if recipe and result.name not in setAvailableAspectNames and set(recipe).issubset(setAvailableAspectNames):
                if not TI.mixAspect(result, 1):
                    logging.warning(f"Could not mix aspect {result.name} while opening all aspects")
        UI.safeRemoveObject(onProcessText)
        UI.setTimeout(0, TI.updateAvailableAspectsInInventory, [detectionAspectsDialogue, [UI, TI]])

    threading.Thread(target=mixAllAspects).start()
```

- [ ] **Step 13: Проверить синтаксис и отсутствие старых вызовов**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src && grep -rn "scrollToLeftSide\|currentAspectsPageIdx\|pointAspectsScroll\|pointAspectsMix\|maxAspectsPagesCount" src/gtnh || echo "OK: no legacy scroll usage in gtnh"
```

Expected: compileall без ошибок; `OK: no legacy scroll usage in gtnh`

- [ ] **Step 14: Прогнать все тесты**

Run: `/tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v`
Expected: все тесты PASS (PyQt-зависимые могут быть skipped)

- [ ] **Step 15: Commit**

```bash
git add src/gtnh/scenarios
git commit -m "feat(gtnh): add two-zone window scenario and detection dialogue"
```

### Step 15b: Обязательные исправления (найдено code review Task 8)

1. Пауза не использует `safeSetKeyCallback` (он сломан: `QTimer.singleShot` не срабатывает из потока клавиатуры). Вместо этого один стабильный `togglePauseState`:
   ```python
   pauseStateFlag = [False]

   def switchToActiveState():
       pauseStateFlag[0] = False
       UI.safeSetAllObjectsVisibility(False)
       UI.safeSetObjectsVisibility(activeStateDialogueObjects, True)
       UI.safeSetObjectsVisibility(cellsObjects, True)

   def switchToPausedState():
       pauseStateFlag[0] = True
       UI.safeSetAllObjectsVisibility(False)
       UI.safeSetObjectsVisibility(pausedStateDialogueObjects, True)

   def togglePauseState():
       if pauseStateFlag[0]:
           switchToActiveState()
       else:
           switchToPausedState()

   UI.setKeyCallback([KeyboardKeys.ctrl, KeyboardKeys.shift, KeyboardKeys.space], togglePauseState)
   ```
   `exitButton` добавляется в `activeStateDialogueObjects`; прямой `exitButton.setVisibility` удаляется.
2. В конце `switchToCellDialogue` повторно регистрировать `togglePauseState` (GUI-поток мыши), чтобы хоткей не терялся после правки ячейки.
3. `openAllAspects`: `mixAllAspects` в `try/except/finally` (`logging.exception`), в `finally` — `safeRemoveObject` + `UI.setTimeout(0, TI.updateAvailableAspectsInInventory, ...)`; поток `daemon=True`.
4. Интерактор: guard по отсутствующим координатам ингредиента (см. Task 7 Step 4b п.7).

---

## Task 9: README и финальная верификация

**Files:**
- Modify: `README.md`
- Verify: весь репозиторий

- [ ] **Step 1: Обновить раздел запуска в `README.md`**

Найти:

```md
2. Добавить папку src проекта в PYTHONPATH:
Windows:
```cmd
set "PYTHONPATH=$($CWD);$($PYTHONPATH)"
```
-Unix:
```cmd
export PYTHONPATH=$(cwd):$PYTHONPATH
```

3. Запуск из корня проекта (требуется версия `Python 3.10` или выше):
```shell
python -m src.main
```
```

Заменить на:

```md
2. Запуск из корня проекта (требуется версия `Python 3.12` или выше, PYTHONPATH не требуется):
```shell
py -3.12 src\main.py
```
или
```shell
py -3.12 -m src.main
```
или через точку входа в корне (удобно для кнопки Run в VS Code):
```shell
py -3.12 main.py
```

3. Выбор режима (edition):
- при первом запуске программа предложит выбрать режим: `Thaumcraft` (оригинальный мод) или `GTNH`;
- выбор сохраняется в AppData и используется при следующих запусках;
- переопределить режим для текущего запуска можно флагом:
```shell
py -3.12 src\main.py --edition gtnh
```
```

- [ ] **Step 2: Полный прогон тестов и синтаксиса**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src configs && /tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v
```

Expected: compileall без ошибок, все тесты PASS/OK, 0 failures.

- [ ] **Step 3: Проверить чистоту рабочего дерева и историю**

Run:

```bash
git status --porcelain
git log --oneline original..HEAD
```

Expected: `git status` пуст; в логе — коммиты задач 1–9.

- [ ] **Step 4: Ручная проверка vanilla-режима (Windows)**

Выполняет пользователь:

```powershell
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py --edition vanilla
```

Чек-лист:
- выбирается язык, показывается `enroll`, настраивается окно, 5×5-зоны и точки скролла/микса присутствуют;
- определение аспектов работает постранично (скролл);
- `Ctrl+Shift+Space` ставит исследование на паузу;
- поведение совпадает с `original`.

- [ ] **Step 5: Ручная проверка GTNH-режима (Windows, клиент GTNH)**

```powershell
py -3.12 main.py --edition gtnh
```

Чек-лист:
- окно настройки содержит две зоны аспектов 4×9 и не содержит точек скролла/микса;
- определение аспектов считывает обе зоны, количество по confidence-фильтру;
- кнопка «Открыть все аспекты» работает, UI не зависает (микс в фоновом потоке);
- `Ctrl+Shift+Space` ставит диалог детекта на паузу и снимает её;
- исследование решается и выкладывается; сверка с `master`.

- [ ] **Step 5b: Проверка упаковки (Windows)**

Собрать exe через auto-py-to-exe по `pyinstaller_configs/autoPyToExe.json` (entry `./src/main.py`, pathex `./src;./`, hidden imports `editions.vanilla` и `gtnh`, datas configs/images/models/gtnh data) и запустить:
- exe стартует без `ModuleNotFoundError`;
- выбирается режим `GTNH`, окно настройки открывается, данные `evolutio` подгружаются.
- при ошибке проверить `pyi-archive_viewer -r -l <exe> | grep gtnh` — модули и `gtnh/data` должны присутствовать.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: describe entry points and edition selection"
```

---

## Self-review: покрытие спеки

| Раздел спеки | Таск(и) |
|---|---|
| 3.1–3.2 bootstrap путей, root main.py, PyInstaller pathex/datas | Task 4 |
| 3.3 Python 3.12 / requirements | Предусловия, Task 9 Step 4 |
| 4.1 точки расширения ядра (editions, applyEdition, createTI, AppState, translations) | Tasks 1–4, 7 |
| 4.2 структура модуля `src/gtnh/` | Tasks 5–8 |
| 4.3 выбор режима (сценарий + флаг + конфиг) | Tasks 3–4 |
| 5.A архитектура сценариев (scenario3/7, override через applyEdition) | Task 8 |
| 5.B двухоконный инвентарь | Task 7 |
| 5.C UI GTNH (openAllAspects, pause) | Task 8 |
| 5.D потокобезопасность (`safe*` в pause/фоновом миксе) | Task 8 |
| 5.E алгоритмы (recognition, mixAspect) | Tasks 6–7 |
| 5.F данные/конфиги/переводы (GTNH recipes, evolutio, TEXTS) | Tasks 3, 5 |
| 5.G запуск и сборка | Tasks 4, 9 |
| 6 маппинг master → модуль | Tasks 5–8 |
| 7 этапы/коммиты | все таски |
| 8 верификация | Tasks 1–9 (тесты/compileall) + Task 9 Steps 4–5 |

Проверки плана:
- **Placeholders:** отсутствуют, весь код приведён полностью.
- **Type consistency:** имена совпадают во всех тасках: `BaseEdition.extraAspectRecipes/extraAddonsRecipes`, `AppState._saveVanillaThaumWindowControls`, `planMixing(aspect, targetCount, getAspectByName, getAspectRecipeByName)`, `GtnhAspect.rectAspectsNumber`, `GtnhEdition.createTI`, `Scenarios.activateEdition/applyEdition/routeStartup`.
- **Известное отступление от спеки:** `TEXTS.chooseEdition` на первом запуске недоступен (язык ещё не выбран), поэтому сценарий использует `AppState.translatedTexts.get(..., DEFAULT_CHOOSE_EDITION_TEXT)`; ключ всё равно добавлен во все 11 языков и применяется при последующих запусках.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-04-gtnh-edition-integration.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session with checkpoints.

Which approach?
