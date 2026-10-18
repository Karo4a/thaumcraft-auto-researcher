import os
import sys
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.translations import TEXTS
from controllers.Scenarios import scenario8_Researchings as scenario
from utils import AppState

PLACE_BUTTON_TEXT = TEXTS.Buttons.placeSolving
INK_TEXT_KEY = TEXTS.solvingInkExhausted
ABORTED_TEXT_KEY = TEXTS.solvingPlacingAborted


class FakePrimitive:
    def __init__(self, name="primitive"):
        self.name = name
        self.visible = True

    def setVisibility(self, state):
        self.visible = state


class FakeUI:
    """Заглушка OverlayUI: сценарию нужны только показанные объекты и переключение видимости."""

    def __init__(self, w=1920, h=1080):
        self.w = w
        self.h = h
        self.objects = []
        self.shown = []
        self.removed = []
        self.timedEvents = []
        self.keyCallbacks = []

    def width(self):
        return self.w

    def height(self):
        return self.h

    def addObject(self, obj):
        self.objects.append(obj)
        return obj

    def clearAll(self):
        self.objects.clear()

    def createExitButton(self, *args, **kwargs):
        return FakePrimitive("exitButton")

    def setAllObjectsVisibility(self, state):
        for obj in self.objects:
            obj.setVisibility(state)

    def setObjectsVisibility(self, objects, state):
        for obj in objects:
            obj.setVisibility(state)

    def setKeyCallback(self, keys, callback, *args):
        self.keyCallbacks.append((tuple(keys), callback))

    def clearKeyCallbacks(self):
        self.keyCallbacks.clear()

    def setTimeout(self, timeoutMs, callback, args=[], kwargs={}, onChangeCallback=lambda timeLeft: None):
        self.timedEvents.append((timeoutMs, callback, args))

    def safeExit(self):
        pass

    def safeRepaint(self):
        pass

    def safeSetAllObjectsVisibility(self, state):
        self.setAllObjectsVisibility(state)

    def safeSetObjectsVisibility(self, objects, state):
        self.setObjectsVisibility(objects, state)

    def safeAddObject(self, obj):
        self.objects.append(obj)
        self.shown.append(obj)

    def safeRemoveObject(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        self.removed.append(obj)

    def safeRemoveObjects(self, objects):
        for obj in objects:
            self.safeRemoveObject(obj)

    def safeClearKeyCallbacks(self):
        self.clearKeyCallbacks()

    def safeSetKeyCallback(self, keys, callback, *args):
        self.keyCallbacks.append((tuple(keys), callback))

    def repaint(self):
        pass

    def removeObject(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        return obj


class FakeAspect:
    def __init__(self, name):
        self.name = name
        self.pixMapImage = None
        self.cellX = 0
        self.cellY = 0


class FakeTI:
    """Заглушка ThaumInteractor: fillByLinkMap повторяет контракт GTNH-версии."""

    hexagonSlotSizeX = 38.0
    hexagonSlotSizeY = 42.0

    def __init__(self, detections, solve):
        self.availableAspects = [FakeAspect("vacuos"), FakeAspect("aer")]
        self.rectHexagonsCC = FakePrimitive("fieldCenter")
        self.rectHexagonsCC.x = 960
        self.rectHexagonsCC.y = 540
        self.detections = list(detections)
        self.detectionCalls = 0
        self.placed = []
        self.papersTakenOut = 0
        self.workingSlotIncreases = 0
        self.solve = solve

    def getExistingAspectsOnField(self):
        self.detectionCalls += 1
        if len(self.detections) > 1:
            return self.detections.pop(0)
        return self.detections[0]

    def getAvailableAspectsNames(self):
        return [aspect.name for aspect in self.availableAspects]

    def getAspectByName(self, name):
        for aspect in self.availableAspects:
            if aspect.name == name:
                return aspect
        return FakeAspect(name)

    def fillByLinkMap(self, aspectsMap, onAspectPlaced=None):
        for coords in sorted(aspectsMap):
            self.placed.append(coords)
            if onAspectPlaced is not None and not onAspectPlaced():
                return False
        return True

    def takeOutPaper(self):
        self.papersTakenOut += 1

    def insertPaper(self):
        pass

    def increaseWorkingSlot(self):
        self.workingSlotIncreases += 1

    def resetWorkingSlot(self):
        pass

    def moveMouseInSafePos(self):
        pass


def makeTranslations():
    texts = {}
    for name, value in vars(TEXTS).items():
        if name.startswith("_") or name == "Buttons" or not isinstance(value, str):
            continue
        texts[value] = value
    for name, value in vars(TEXTS.Buttons).items():
        if name.startswith("_") or not isinstance(value, str):
            continue
        texts[value] = value
    return texts


def hexagonShape(radius):
    """Клетки гексагонального поля, как их строит ThaumInteractor.getExistingAspectsOnField."""
    return {(x, y) for x in range(-radius, radius + 1)
            for y in range(-radius + (abs(x) + 1) // 2, radius - abs(x) // 2 + 1)}


RADIUS = 2
ASPECT_CELL = (-2, -1)
# Маркерные клетки, попадающие в поле радиуса 2: центральная полоса целиком
BAND = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1)}


def fieldDetection(inkExhausted=False, lostBandCells=frozenset()):
    """Определение поля радиуса 2, как в реальном логе игры.

    inkExhausted=True — плашка "You have run out of ink!" закрыла всю центральную полосу.
    lostBandCells — отдельные клетки полосы, которые просто не опознались (промахи определения).
    """
    shape = hexagonShape(RADIUS)
    aspects = {ASPECT_CELL: "aer"}
    lostCells = set(lostBandCells)
    if inkExhausted:
        lostCells |= BAND
    freeHexagons = (shape - set(aspects)) - lostCells
    noneHexagons = shape - freeHexagons  # аспекты остаются в noneHexagons, как в оригинале
    return dict(aspects), noneHexagons, freeHexagons


SOLVE = {ASPECT_CELL: "aer", (1, -1): "vacuos", (2, -1): "aer", (1, 2): "ignis", (2, 1): "terra"}
# Что реально должно быть выложено: решение без аспектов, уже стоящих на поле
PLANNED_CELLS = sorted(set(SOLVE) - {ASPECT_CELL})


class Scenario8InkExhaustionTest(unittest.TestCase):
    def setUp(self):
        self.originalTranslatedTexts = AppState.translatedTexts
        self.originalMarkerCells = scenario.INK_EXHAUSTED_MARKER_CELLS
        self.originalCheckEvery = scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS
        self.originalGenerateLinkMap = scenario.generateLinkMap
        self.originalRenderDelay = scenario.renderDelay
        self.originalEventsDelay = scenario.eventsDelay
        AppState.translatedTexts = makeTranslations()
        scenario.generateLinkMap = lambda *args, **kwargs: dict(SOLVE)
        scenario.renderDelay = lambda: None
        scenario.eventsDelay = lambda: None

    def tearDown(self):
        AppState.translatedTexts = self.originalTranslatedTexts
        scenario.INK_EXHAUSTED_MARKER_CELLS = self.originalMarkerCells
        scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS = self.originalCheckEvery
        scenario.generateLinkMap = self.originalGenerateLinkMap
        scenario.renderDelay = self.originalRenderDelay
        scenario.eventsDelay = self.originalEventsDelay

    def runScenario(self, ti):
        UI = FakeUI()
        scenario.runResearching(UI, ti)

        buttons = [obj for obj in UI.objects if getattr(obj, "text", None) == PLACE_BUTTON_TEXT]
        self.assertEqual(len(buttons), 1, "кнопка «Выложить решение» не найдена")
        buttons[0].onClickCallback()
        for thread in threading.enumerate():
            if thread is not threading.current_thread():
                thread.join(timeout=10)
        return UI

    def shownTexts(self, UI):
        return [obj.text for obj in UI.shown if getattr(obj, "text", None) is not None]

    def test_placing_is_disabled_when_the_inkwell_is_empty(self):
        ti = FakeTI([fieldDetection(inkExhausted=True)], SOLVE)
        UI = self.runScenario(ti)
        self.assertEqual(ti.placed, [])
        self.assertEqual(ti.papersTakenOut, 0)
        self.assertIn(INK_TEXT_KEY, self.shownTexts(UI))

    def test_placing_is_aborted_when_the_inkwell_empties_mid_run(self):
        scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS = 3
        ti = FakeTI([fieldDetection(inkExhausted=False), fieldDetection(inkExhausted=True)], SOLVE)
        UI = self.runScenario(ti)
        # 3 аспекта выложены, после проверки поля выкладывание прервано
        self.assertEqual(len(ti.placed), 3)
        self.assertEqual(ti.papersTakenOut, 0)
        self.assertEqual(ti.workingSlotIncreases, 0)
        self.assertIn(INK_TEXT_KEY, self.shownTexts(UI))
        self.assertNotIn(ABORTED_TEXT_KEY, self.shownTexts(UI))

    def test_placing_resumes_after_the_ink_is_refilled(self):
        # Пользователь пополнил чернильницу: перед отказом поле определяется заново,
        # поэтому кнопка «Выложить решение» снова работает
        ti = FakeTI([fieldDetection(inkExhausted=True), fieldDetection(inkExhausted=False)], SOLVE)
        UI = self.runScenario(ti)
        self.assertEqual(sorted(ti.placed), PLANNED_CELLS)
        self.assertEqual(ti.papersTakenOut, 1)
        self.assertNotIn(INK_TEXT_KEY, self.shownTexts(UI))

    def test_placing_is_not_interrupted_by_sporadic_detection_misses(self):
        # Ложное срабатывание из живого прогона: часть клеток полосы не опознана,
        # но чернила на месте — выкладывание не прерываем
        scenario.INK_CHECK_EVERY_N_PLACED_ASPECTS = 1
        ti = FakeTI([fieldDetection(lostBandCells={(-2, 0), (0, 0), (1, 1)})], SOLVE)
        UI = self.runScenario(ti)
        self.assertEqual(sorted(ti.placed), PLANNED_CELLS)
        self.assertEqual(ti.papersTakenOut, 1)
        self.assertNotIn(INK_TEXT_KEY, self.shownTexts(UI))

    def test_placing_is_not_interrupted_when_tracking_is_disabled(self):
        # Пустой набор маркерных клеток = поведение до фичи
        scenario.INK_EXHAUSTED_MARKER_CELLS = set()
        ti = FakeTI([fieldDetection(inkExhausted=False), fieldDetection(inkExhausted=True)], SOLVE)
        UI = self.runScenario(ti)
        self.assertEqual(sorted(ti.placed), PLANNED_CELLS)
        self.assertEqual(ti.papersTakenOut, 1)
        self.assertNotIn(INK_TEXT_KEY, self.shownTexts(UI))
        # При выключенном отслеживании лишних определений поля нет:
        # одно перед выкладыванием + одно для следующего исследования
        self.assertEqual(ti.detectionCalls, 2)


if __name__ == "__main__":
    unittest.main()