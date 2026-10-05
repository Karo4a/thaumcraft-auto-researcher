# GTNH Open-All-Aspects Multi-Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the GTNH "Open all aspects" button open every reachable aspect in one press by repeating the mixing pass with an inventory re-scan between passes.

**Architecture:** Extract the per-pass selection into a pure, testable helper `selectCraftableAspects()` in `src/gtnh/mixing.py`. Rewrite `openAllAspects()` in `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py` as a callback loop: mix a pass in a background thread, schedule `updateAvailableAspectsInInventory` on the GUI thread, then either start the next pass (if new aspects appeared) or finish. Coordinates and counts (including the +3 for a newly opened aspect) are always read fresh from the game by the re-scan, so no yield simulation is needed.

**Tech Stack:** Python (target 3.12 on Windows), PyQt5, `threading`, `unittest`. Local WSL test venv has no PyQt5, so only the pure helper is unit-tested locally; the UI/threading loop is verified by `compileall` plus the manual Windows checklist.

**Test interpreter (WSL):** `/tmp/opencode/taum-test-venv/bin/python` — run from repo root `/mnt/e/Learning/ThaumcraftAutoResearch/thaumcraft-auto-researcher`.

---

### Task 1: Pure helper `selectCraftableAspects` (TDD)

**Files:**
- Modify: `src/gtnh/mixing.py`
- Test: `tests/test_gtnh_mixing.py`

- [ ] **Step 1: Write the failing tests**

In `tests/test_gtnh_mixing.py`, change the import line:

```python
from gtnh.mixing import planMixing
```

to:

```python
from gtnh.mixing import planMixing, selectCraftableAspects
```

and add this test class just before the `if __name__ == "__main__":` block:

```python
class SelectCraftableAspectsTest(unittest.TestCase):
    def test_returns_only_missing_craftable_in_order(self):
        allNames = ["aer", "vacuos", "potentia", "praecantatio"]
        available = {"aer", "perditio", "ordo", "ignis"}
        self.assertEqual(
            selectCraftableAspects(allNames, RECIPES, available),
            ["vacuos", "potentia"],
        )

    def test_skips_already_available(self):
        self.assertEqual(
            selectCraftableAspects(["vacuos"], RECIPES, {"aer", "perditio", "vacuos"}),
            [],
        )

    def test_skips_basics_and_missing_ingredients(self):
        self.assertEqual(
            selectCraftableAspects(["aer", "praecantatio"], RECIPES, {"vacuos", "ordo"}),
            [],
        )

    def test_returns_deeper_aspect_when_ingredients_present(self):
        self.assertEqual(
            selectCraftableAspects(["praecantatio"], RECIPES, {"vacuos", "potentia"}),
            ["praecantatio"],
        )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_mixing -v
```

Expected: FAIL/ERROR with `ImportError: cannot import name 'selectCraftableAspects' from 'gtnh.mixing'`.

- [ ] **Step 3: Implement the helper**

Append to `src/gtnh/mixing.py` (after `planMixing`):

```python
def selectCraftableAspects(allAspectNames: list[str], recipes: dict[str, list[str]],
                           availableNames: set[str]) -> list[str]:
    """
    Возвращает имена аспектов (в порядке allAspectNames), которые сейчас можно скрафтить:
    аспект ещё не открыт, у него есть рецепт, и оба ингредиента уже доступны.
    """
    craftable = []
    for name in allAspectNames:
        if name in availableNames:
            continue
        recipe = recipes.get(name)
        if recipe and set(recipe).issubset(availableNames):
            craftable.append(name)
    return craftable
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest tests.test_gtnh_mixing -v
```

Expected: PASS (all `MixingPlanTest` plus the 4 new tests).

- [ ] **Step 5: Commit**

```bash
git add src/gtnh/mixing.py tests/test_gtnh_mixing.py
git commit -m "feat(gtnh): add selectCraftableAspects helper"
```

---

### Task 2: Multi-pass `openAllAspects` with re-scan

**Files:**
- Modify: `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py` (imports; replace `openAllAspects`, currently lines 349-378)

No local unit test (imports PyQt5). Verification is `compileall` plus the manual Windows checklist.

- [ ] **Step 1: Add the helper import**

In `src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py`, after the line `from gtnh.constants import RECT_ASPECTS_NUMBERS, THAUM_ASPECTS_INVENTORY_SLOTS_X, THAUM_ASPECTS_INVENTORY_SLOTS_Y`, add:

```python
from gtnh.mixing import selectCraftableAspects
```

- [ ] **Step 2: Replace `openAllAspects`**

Replace the entire existing function:

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
        try:
            setAvailableAspectNames = set(map(lambda aspect: aspect.name, TI.availableAspects))
            for result in TI.allAspects:
                recipe = TI.getAspectRecipeByName(result.name)
                if recipe and result.name not in setAvailableAspectNames and set(recipe).issubset(setAvailableAspectNames):
                    if not TI.mixAspect(result, 1):
                        logging.warning(f"Could not mix aspect {result.name} while opening all aspects")
        except Exception:
            logging.exception("Error while opening all aspects")
        finally:
            UI.safeRemoveObject(onProcessText)
            UI.setTimeout(0, TI.updateAvailableAspectsInInventory, [detectionAspectsDialogue, [UI, TI]])

    threading.Thread(target=mixAllAspects, daemon=True).start()
```

with:

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

    initialNames = set(map(lambda aspect: aspect.name, TI.availableAspects))
    maxPasses = len(TI.allAspects) + 1

    def finish(mixedTotal):
        logging.info(f"Open all aspects finished. Mixed total: {mixedTotal}")
        UI.safeRemoveObject(onProcessText)
        detectionAspectsDialogue(UI, TI)

    def runPass(passIndex, previousNames, mixedTotal):
        def mixPass():
            mixedThisPass = 0
            try:
                availableNames = set(map(lambda aspect: aspect.name, TI.availableAspects))
                craftableNames = selectCraftableAspects(
                    [aspect.name for aspect in TI.allAspects], TI.recipes, availableNames)
                logging.info(f"Open all aspects pass {passIndex}: craftable {craftableNames}")
                for name in craftableNames:
                    if TI.mixAspect(TI.getAspectByName(name), 1):
                        mixedThisPass += 1
                    else:
                        logging.warning(f"Could not mix aspect {name} while opening all aspects")
            except Exception:
                logging.exception(f"Error while opening all aspects (pass {passIndex})")
            finally:
                UI.setTimeout(0, TI.updateAvailableAspectsInInventory,
                              [afterDetection, [passIndex, previousNames, mixedTotal + mixedThisPass]])

        threading.Thread(target=mixPass, daemon=True).start()

    def afterDetection(passIndex, previousNames, mixedTotal):
        currentNames = set(map(lambda aspect: aspect.name, TI.availableAspects))
        if passIndex < maxPasses and currentNames != previousNames:
            runPass(passIndex + 1, currentNames, mixedTotal)
        else:
            finish(mixedTotal)

    runPass(1, initialNames, 0)
```

Notes:
- `previousNames` is the set of available aspect names captured **before** the pass; the re-scan happens in the `finally` via `UI.setTimeout(0, TI.updateAvailableAspectsInInventory, [afterDetection, ...])`, then `afterDetection` compares the refreshed set. If new names appeared, the next pass runs; otherwise it finishes.
- This intentionally relies on the game re-scan: a newly mixed aspect's cell coordinates only exist after `updateAvailableAspectsInInventory`, so chaining is done pass-by-pass, not inside one pass. The +3 yield for a new aspect is therefore read from the game, not simulated.
- `maxPasses = len(TI.allAspects) + 1` is a safety bound against an infinite loop.
- `finish` and the re-scan schedule both run on the GUI thread (`setTimeout` callbacks); the mixing itself stays on the background thread.

- [ ] **Step 3: Byte-compile**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py && echo OK
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/gtnh/scenarios/scenario7_DetectionAspectsDialogue.py
git commit -m "feat(gtnh): open all aspects over multiple scanned passes"
```

---

### Task 3: Full local verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole test suite**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS, `Ran 56 tests ... OK (skipped=7)` (52 previous + 4 new helper tests); exact count may differ, requirement is `OK` with 7 skips and no failures.

- [ ] **Step 2: Byte-compile the whole source tree**

Run:

```bash
/tmp/opencode/taum-test-venv/bin/python -m compileall -q src configs main.py && echo OK
```

Expected: `OK`

- [ ] **Step 3: Confirm the working tree only contains the intended changes**

Run:

```bash
git status --porcelain
```

Expected: only the files touched by Tasks 1-2 (plus any pre-existing uncommitted work). No unexpected files.

- [ ] **Step 4: Hand off manual Windows checks**

Report that the following require the game + PyQt5 and remain to be verified manually on Windows. Do not claim they passed:

1. Start GTNH edition with several aspects still locked.
2. Press "Open all aspects"; confirm the log shows multiple `Open all aspects pass N: craftable [...]` lines and that aspects keep opening pass by pass.
3. Confirm it stops on its own when no more aspects are craftable (no infinite pass loop).
4. Confirm the process text disappears and the detection dialogue (`detectionAspectsDialogue`) appears at the end.
5. Confirm no crash/freeze during mixing or between scans (scan runs briefly on the GUI thread).
6. Sanity: if the neural-net scan misses a just-created aspect, its dependent aspects may not open that run — re-pressing the button continues from the newly detected state (known limitation of the re-scan approach).

---

## Notes for the implementer

- Do not change `planMixing`, `mixAspect`, or `updateAvailableAspectsInInventory`; approach A reuses them as-is.
- Keep `openAllAspects` behavior when there is nothing to craft: it must still end with `detectionAspectsDialogue`.
- The helper is pure and must stay free of PyQt/UI imports.
