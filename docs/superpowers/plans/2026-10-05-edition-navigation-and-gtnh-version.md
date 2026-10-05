# Edition Navigation Back Button and GTNH Version Scenario Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a back button to the language-selection scenario that returns to edition selection, and give the GTNH edition its own scenario-4 version picker showing only GTNH modpack versions.

**Architecture:** Part 1 reuses `createNextBackButtonsAndText` with `Scenarios.chooseEdition` as the back callback. Part 2 adds `getGtnhVersions()` to the `gtnh` package, a new translated text key, an isolated copy of scenario 4 under `src/gtnh/scenarios/`, makes `chooseThaumVersion` overridable via `_DEFAULT_SCENARIOS`, and registers the GTNH override in `GtnhEdition.scenarioOverrides`.

**Tech Stack:** Python (target 3.12 on Windows), PyQt5, `unittest`. Local WSL test venv has no PyQt5, so UI scenario modules and `scenarioOverrides` cannot be imported locally; those are verified by `compileall` plus the manual Windows checklist in spec §7.

**Test interpreter (WSL):** `/tmp/opencode/taum-test-venv/bin/python` — run all commands from the repo root `/mnt/e/Learning/ThaumcraftAutoResearch/thaumcraft-auto-researcher-gtnh`.

**Spec:** `docs/superpowers/specs/2026-10-05-edition-navigation-and-gtnh-version-design.md`

---

### Task 1: Back button on the language screen

**Files:**
- Modify: `src/controllers/Scenarios/scenario0_Language.py:26-33`

No local unit test: the module imports PyQt5, absent in the WSL venv. Verification is `compileall` plus manual Windows checklist (spec §7 items 1-3).

- [ ] **Step 1: Replace the `createNextBackButtonsAndText` call**

Replace this exact block (currently around lines 26-33):

```python
    (infoText, nextButton, _) = createNextBackButtonsAndText(
        UI,
        f"""Select language""",
        onSubmit, [],
        None, [],
        "Go next >",
        None
    )
```

with:

```python
    (infoText, backButton, nextButton) = createNextBackButtonsAndText(
        UI,
        f"""Select language""",
        onSubmit, [],
        Scenarios.chooseEdition, [UI],
        "Go next >",
        "< Back",
    )
```

Notes:
- The helper returns `(mainText, back, next)` when both callbacks are set, so the second element is the back button and the third is the next button. The layout code below (`updateTextsPosition`) already uses `nextButton.y` / `nextButton.h`; keep those references unchanged.
- `overrideBackText="< Back"` is required because `AppState.translatedTexts` is empty on this screen (no language saved yet); the helper would otherwise KeyError on `TEXTS.Buttons.backArrowed`.

- [ ] **Step 2: Byte-compile**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src/controllers/Scenarios/scenario0_Language.py && echo OK
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/controllers/Scenarios/scenario0_Language.py
git commit -m "feat(scenarios): add back button to language selection"
```

---

### Task 2: `getGtnhVersions()` helper

**Files:**
- Modify: `src/gtnh/__init__.py:57` (after `createEdition`)
- Test: `tests/test_gtnh_edition.py` (add one method to `GtnhEditionTest`)

- [ ] **Step 1: Write the failing test**

Add this method inside `class GtnhEditionTest` in `tests/test_gtnh_edition.py` (after `test_extra_recipes_loaded`):

```python
    def test_get_gtnh_versions(self):
        from gtnh import getGtnhVersions
        self.assertEqual(getGtnhVersions(), ["GTNH"])
```

(The import is local so that only this test fails before the helper exists, instead of breaking the whole test module at collection time.)

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_edition.GtnhEditionTest.test_get_gtnh_versions -v
```

Expected: FAIL with `ImportError: cannot import name 'getGtnhVersions' from 'gtnh'`.

- [ ] **Step 3: Implement the helper**

Append to `src/gtnh/__init__.py` after the `createEdition` function:

```python
def getGtnhVersions() -> list[str]:
    return list(createEdition().extraAspectRecipes().keys())
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_edition.GtnhEditionTest.test_get_gtnh_versions -v
```

Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/gtnh/__init__.py tests/test_gtnh_edition.py
git commit -m "feat(gtnh): add getGtnhVersions helper"
```

---

### Task 3: `chooseGtnhVersion` translation key

**Files:**
- Modify: `configs/translations.py` (TEXTS class near line 11; each of the 11 language dicts)
- Test: `tests/test_translations.py:34-38`

- [ ] **Step 1: Write the failing test**

In `tests/test_translations.py`, replace the body of `test_new_edition_texts_are_translated`:

```python
    def test_new_edition_texts_are_translated(self):
        for language, texts in TRANSLATIONS.items():
            for key in (TEXTS.chooseEdition, TEXTS.openAllAspects):
                self.assertTrue(texts[key], f"{language} has empty {key}")
                self.assertNotEqual(texts[key], key, f"{language} did not translate {key}")
```

with:

```python
    def test_new_edition_texts_are_translated(self):
        for language, texts in TRANSLATIONS.items():
            for key in (TEXTS.chooseEdition, TEXTS.openAllAspects, TEXTS.chooseGtnhVersion):
                self.assertTrue(texts[key], f"{language} has empty {key}")
                self.assertNotEqual(texts[key], key, f"{language} did not translate {key}")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_translations -v
```

Expected: ERROR/FAIL with `AttributeError: chooseGtnhVersion` (the `TEXTS` attribute does not exist yet).

- [ ] **Step 3: Add the TEXTS key**

In `configs/translations.py`, in `class TEXTS`, add a line immediately after `chooseThaumVersion = "chooseThaumVersion"`:

```python
    chooseGtnhVersion = "chooseGtnhVersion"
```

- [ ] **Step 4: Add the translation to all 11 languages**

Immediately after each language's `TEXTS.languageName: "<native name>",` line, add the corresponding entry:

| Dict | Anchor line | Add line |
|---|---|---|
| `"Russian"` | `TEXTS.languageName: "Русский",` | `TEXTS.chooseGtnhVersion: "Выберите версию сборки GTNH.",` |
| `"English"` | `TEXTS.languageName: "English",` | `TEXTS.chooseGtnhVersion: "Choose the GTNH modpack version.",` |
| `"Italian"` | `TEXTS.languageName: "Italiano",` | `TEXTS.chooseGtnhVersion: "Scegli la versione della modpack GTNH.",` |
| `"Dutch"` | `TEXTS.languageName: "Nederlands",` | `TEXTS.chooseGtnhVersion: "Kies de GTNH-modpackversie.",` |
| `"Spanish"` | `TEXTS.languageName: "Español",` | `TEXTS.chooseGtnhVersion: "Elige la versión del modpack de GTNH.",` |
| `"Arabic"` | `TEXTS.languageName: "العربية",` | `TEXTS.chooseGtnhVersion: "اختر إصدار تجميعة GTNH.",` |
| `"Chinese (Traditional)"` | `TEXTS.languageName: "繁體中文",` | `TEXTS.chooseGtnhVersion: "選擇 GTNH 整合包版本。",` |
| `"Chinese (Simplified)"` | `TEXTS.languageName: "简体中文",` | `TEXTS.chooseGtnhVersion: "选择 GTNH 整合包版本。",` |
| `"French"` | `TEXTS.languageName: "Français",` | `TEXTS.chooseGtnhVersion: "Choisissez la version du modpack GTNH.",` |
| `"Hindi"` | `TEXTS.languageName: "हिन्दी",` | `TEXTS.chooseGtnhVersion: "GTNH मॉडपैक संस्करण चुनें।",` |
| `"Korean"` | `TEXTS.languageName: "한국어",` | `TEXTS.chooseGtnhVersion: "GTNH 모드팩 버전을 선택하세요.",` |

Important: the `TEXTS.languageName` values above are the *actual* values already present in each dict (verified at `configs/translations.py:49,153,257,361,465,569,673,776,879,983,1087`). Each added string must be a real translation (the test asserts it is not equal to the key).

- [ ] **Step 5: Run the translation tests to verify they pass**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_translations -v
```

Expected: PASS (2 tests), including `test_all_languages_have_all_texts`.

- [ ] **Step 6: Commit**

```bash
git add configs/translations.py tests/test_translations.py
git commit -m "feat(translations): add chooseGtnhVersion text"
```

---

### Task 4: GTNH scenario 4 module

**Files:**
- Create: `src/gtnh/scenarios/scenario4_ChooseThaumVersion.py`

No local unit test (imports PyQt5). Verification is `compileall` plus manual Windows checklist (spec §7 item 4).

- [ ] **Step 1: Create the module**

Create `src/gtnh/scenarios/scenario4_ChooseThaumVersion.py` with exactly this content:

```python
import logging

from PyQt5.QtGui import QColor

from UI.OverlayUI import OverlayUI
from UI.primitives import Text
from configs.translations import TEXTS
from controllers import Scenarios
from controllers.Scenarios.shared import createNextBackButtonsAndText, PointTextAnchor
from configs.constants import MARGIN
from gtnh import getGtnhVersions
from utils import AppState


def chooseThaumVersion(UI: OverlayUI):
    UI.clearAll()
    UI.createExitButton()

    def onSubmit():
        if selectedVersion[0] is None:
            logging.warning(f"Trying to go next but thaum version is not selected")
            return
        logging.info(f"Selected thaum version: {selectedVersion[0]}")
        AppState.saveThaumVersion(selectedVersion[0])
        Scenarios.beReadyForCreatingTI(UI)

    (infoText, backButton, nextButton) = createNextBackButtonsAndText(
        UI,
        AppState.translatedTexts[TEXTS.chooseGtnhVersion],
        onSubmit, [],
        Scenarios.configureThaumWindowCoords, [UI],
    )
    versions = getGtnhVersions()
    versionsObjects = []

    selectedVersionObject: list[Text | None] = [None]
    selectedVersion: list[str | None] = [None]

    oldVersion = AppState.selectedThaumVersion
    if oldVersion is None:
        oldVersion = "GTNH"
        logging.info(f"Selected version in config is none. Selecting default: {oldVersion}")
    else:
        logging.info(f"Selected in config version is: {oldVersion}")

    oldInfoTextCallback = infoText.onMoveCallback
    def updateVersionsPosition():
        oldInfoTextCallback()
        startCurY = nextButton.y + nextButton.h + MARGIN * 2
        curY = startCurY
        curX = PointTextAnchor.x
        for i in range(len(versionsObjects)):
            versionObject = versionsObjects[i]
            if curY > UI.height() - versionObject.h:
                curX += 300
                curY = startCurY
            versionObject.y = curY
            versionObject.x = curX
            curY += versionObject.h + MARGIN

    infoText.LT.onMoveCallback = updateVersionsPosition
    infoText.onMoveCallback = updateVersionsPosition
    startCurY = nextButton.y + nextButton.h + MARGIN * 2
    curY = startCurY
    curX = PointTextAnchor.x
    for i in range(len(versions)):
        version = versions[i]

        def onClickVersion(versionObject, version):
            logging.debug(f"Click on version {version}")
            selectVersion(versionObject, version)

        def selectVersion(versionObject, version):
            if selectedVersionObject[0] is not None:
                selectedVersionObject[0].setColor(QColor('white'))
            logging.debug(f"Version {version} selected in UI. Previous selected version is {selectedVersion[0]}")
            selectedVersion[0] = version
            selectedVersionObject[0] = versionObject
            selectedVersionObject[0].setColor(QColor('purple'))

        versionObject = UI.addObject(Text(
            0, 0,
            version,
            color=QColor('white'),
            withBackground=True,
            padding=MARGIN,
            UI=UI,
            onClickCallback=onClickVersion,
            hoverable=True,
        ))
        if curY > UI.height() - versionObject.h:
            curX += 300
            curY = startCurY
        versionObject.x = curX
        versionObject.y = curY
        curY += versionObject.h + MARGIN
        versionObject.onClickCallbackArgs = [versionObject, version]
        versionsObjects.append(versionObject)
        if oldVersion == version:
            selectVersion(versionObject, version)

    logging.info(f"Selecting version dialogue showed. Versions: {versions}")
```

This is a copy of `src/controllers/Scenarios/scenario4_ChooseThaumVersion.py` with exactly three differences: the title text (`TEXTS.chooseGtnhVersion`), the version source (`getGtnhVersions()`), and the default selected version (`"GTNH"`).

- [ ] **Step 2: Byte-compile**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src/gtnh/scenarios/scenario4_ChooseThaumVersion.py && echo OK
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/gtnh/scenarios/scenario4_ChooseThaumVersion.py
git commit -m "feat(gtnh): add dedicated GTNH version selection scenario"
```

---

### Task 5: Make scenario 4 overridable and register the GTNH override

**Files:**
- Modify: `src/controllers/Scenarios/__init__.py:14-17` (`_DEFAULT_SCENARIOS`)
- Modify: `src/gtnh/__init__.py:22-29` (`GtnhEdition.scenarioOverrides`)

No local unit test (both paths ultimately import the PyQt5 scenario module). Verification is `compileall` plus manual Windows checklist (spec §7 item 4).

- [ ] **Step 1: Add `chooseThaumVersion` to `_DEFAULT_SCENARIOS`**

In `src/controllers/Scenarios/__init__.py`, replace:

```python
_DEFAULT_SCENARIOS = {
    "confirmThaumWindowSlots": confirmThaumWindowSlots,
    "detectionAspectsDialogue": detectionAspectsDialogue,
}
```

with:

```python
_DEFAULT_SCENARIOS = {
    "confirmThaumWindowSlots": confirmThaumWindowSlots,
    "chooseThaumVersion": chooseThaumVersion,
    "detectionAspectsDialogue": detectionAspectsDialogue,
}
```

- [ ] **Step 2: Register the GTNH override**

In `src/gtnh/__init__.py`, replace the body of `scenarioOverrides`:

```python
    @property
    def scenarioOverrides(self) -> dict:
        from gtnh.scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
        from gtnh.scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
        return {
            "confirmThaumWindowSlots": confirmThaumWindowSlots,
            "detectionAspectsDialogue": detectionAspectsDialogue,
        }
```

with:

```python
    @property
    def scenarioOverrides(self) -> dict:
        from gtnh.scenarios.scenario3_ConfirmThaumWindowSlots import confirmThaumWindowSlots
        from gtnh.scenarios.scenario4_ChooseThaumVersion import chooseThaumVersion as gtnhChooseThaumVersion
        from gtnh.scenarios.scenario7_DetectionAspectsDialogue import detectionAspectsDialogue
        return {
            "confirmThaumWindowSlots": confirmThaumWindowSlots,
            "chooseThaumVersion": gtnhChooseThaumVersion,
            "detectionAspectsDialogue": detectionAspectsDialogue,
        }
```

- [ ] **Step 3: Byte-compile both files**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src/controllers/Scenarios/__init__.py src/gtnh/__init__.py && echo OK
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/controllers/Scenarios/__init__.py src/gtnh/__init__.py
git commit -m "feat(editions): allow overriding chooseThaumVersion per edition"
```

---

### Task 6: Full local verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS, `Ran 46 tests ... OK (skipped=7)` (45 previous + `test_get_gtnh_versions`; the new translation key is covered by the existing 2 translation tests). Exact count may differ; requirement is `OK` with 7 skips and no failures.

- [ ] **Step 2: Byte-compile the whole source tree**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src configs main.py && echo OK
```

Expected: `OK`

- [ ] **Step 3: Confirm the working tree is clean**

Run:

```bash
git status --porcelain
```

Expected: no output.

- [ ] **Step 4: Hand off manual Windows checks**

Report to the user that spec §7 items 1-6 remain to be verified manually on Windows (no PyQt5 in the WSL venv). Do not claim those checks passed.

---

## Notes for the implementer

- Do not modify `src/controllers/Scenarios/scenario4_ChooseThaumVersion.py` (the vanilla default); only make it overridable in Task 5.
- Do not add multiple GTNH versions; the single `"GTNH"` key is intentional (spec §2/§6).
- The `backButton` variable in Task 1 and Task 4 is intentionally the unpacked back button; layout uses `nextButton`.
