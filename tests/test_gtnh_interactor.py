import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

INTERACTOR_IMPORT_ERROR = ""
try:
    import gtnh.interactor as interactorModule
    from gtnh.interactor import GtnhThaumInteractor
    HAS_INTERACTOR = True
except ImportError as error:
    HAS_INTERACTOR = False
    INTERACTOR_IMPORT_ERROR = repr(error)


class FakeAspect:
    nextUid = 0

    def __init__(self, name, count=0):
        self.name = name
        self.uid = FakeAspect.nextUid
        FakeAspect.nextUid += 1
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

with open(os.path.join(ROOT, "src", "gtnh", "data", "aspects_configs", "gtnhAspectsRecipes.json"),
          encoding="utf-8") as file:
    GTNH_RECIPES = json.load(file)["GTNH"]


def makeInteractor(recipes=None):
    recipes = recipes or RECIPES
    interactorModule.eventsDelay = lambda: None
    interactorModule.renderDelay = lambda: None
    ti = GtnhThaumInteractor.__new__(GtnhThaumInteractor)
    ti.recipes = recipes
    ti.allAspects = []
    ti.taken = []
    ti.placed = []

    class FakePoint:
        def click(self, button=None):
            pass

        def release(self):
            pass

    def makeAspects(counts=None):
        counts = counts or {}
        aspects = {}
        for name, recipe in recipes.items():
            aspects[name] = FakeAspect(name, counts.get(name, 5 if len(recipe) == 0 else 0))
        ti.allAspects = list(aspects.values())
        return aspects

    ti.makeAspects = makeAspects
    ti.takeAspectByCellCoords = lambda cellX, cellY, rectAspectNumber: ti.taken.append((cellX, cellY, rectAspectNumber))
    ti.inventoryCellCoordsToPixelCoords = lambda cellX, cellY, rectAspectNumber: FakePoint()
    ti.putAspect = lambda cellX, cellY: ti.placed.append((cellX, cellY))
    return ti


@unittest.skipUnless(HAS_INTERACTOR, f"gtnh.interactor import failed: {INTERACTOR_IMPORT_ERROR}")
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

    def test_mix_aborts_before_clicks_when_ingredients_insufficient(self):
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

    def test_mix_aborts_before_clicks_when_gtnh_plan_is_impossible(self):
        # basics на нуле: fabrico скрафтить нельзя, поэтому не должно быть ни одного клика
        ti = makeInteractor(GTNH_RECIPES)
        aspects = ti.makeAspects({name: 0 for name in GTNH_RECIPES})
        self.assertFalse(ti.mixAspect(aspects["fabrico"], 1))
        self.assertEqual(ti.taken, [])
        self.assertEqual(aspects["fabrico"].count, 0)

    def test_mix_aborts_when_ingredient_has_no_coords(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["ordo"].cellX = None
        originalPlanMixing = interactorModule.planMixing
        interactorModule.planMixing = lambda *args, **kwargs: [(aspects["potentia"], 1)]
        try:
            self.assertFalse(ti.mixAspect(aspects["vacuos"], 1))
        finally:
            interactorModule.planMixing = originalPlanMixing
        self.assertEqual(ti.taken, [])

    def test_mix_already_enough_returns_true(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["vacuos"].count = 3
        self.assertTrue(ti.mixAspect(aspects["vacuos"], 1))
        self.assertEqual(ti.taken, [])

    def test_take_aspect_skips_when_cannot_mix(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["vacuos"].count = 0
        aspects["aer"].count = 0
        aspects["perditio"].count = 0
        self.assertFalse(ti.takeAspect(aspects["vacuos"]))
        self.assertEqual(ti.taken, [])
        self.assertEqual(aspects["vacuos"].count, 0)

    def test_take_aspect_returns_false_when_cell_coords_unknown(self):
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["vacuos"].cellX = None
        self.assertFalse(ti.takeAspect(aspects["vacuos"]))
        self.assertEqual(ti.taken, [])

    def test_fill_by_link_map_places_all_aspects(self):
        ti = makeInteractor()
        ti.makeAspects()
        self.assertTrue(ti.fillByLinkMap({(-1, 0): "vacuos", (0, 0): "potentia"}))
        self.assertEqual(sorted(ti.placed), [(-1, 0), (0, 0)])
        self.assertTrue(ti.taken)

    def test_fill_by_link_map_aborts_and_places_nothing_when_aspect_unavailable(self):
        ti = makeInteractor()
        ti.makeAspects({name: 0 for name in RECIPES})
        self.assertFalse(ti.fillByLinkMap({(-1, 0): "vacuos", (0, 0): "potentia"}))
        self.assertEqual(ti.taken, [])
        self.assertEqual(ti.placed, [])

    def test_fill_by_link_map_mixes_missing_ingredients(self):
        # Регресс на лог: fabrico требовал bestia x2 при motus(1) в стоке
        ti = makeInteractor(GTNH_RECIPES)
        aspects = ti.makeAspects({name: 10 for name, recipe in GTNH_RECIPES.items() if not recipe})
        aspects["motus"].count = 1
        aspects["victus"].count = 2
        self.assertTrue(ti.fillByLinkMap({(-1, 0): "fabrico"}))
        self.assertEqual(aspects["fabrico"].count, 0)
        self.assertEqual(ti.placed, [(-1, 0)])
        self.assertTrue(ti.taken)

    def test_mix_after_plan_and_counts_check_is_not_needed(self):
        # Проверка плана целиком: кликов не делаем, если итогового запаса не хватит
        ti = makeInteractor()
        aspects = ti.makeAspects()
        aspects["aer"].count = 4
        aspects["perditio"].count = 4
        aspects["vacuos"].count = 0
        self.assertTrue(ti.mixAspect(aspects["vacuos"], 1))
        self.assertEqual(aspects["vacuos"].count, 1)
        self.assertEqual(aspects["aer"].count, 3)

    def test_fill_by_link_map_calls_placed_callback_for_every_aspect(self):
        ti = makeInteractor()
        ti.makeAspects()
        calls = []

        def onPlaced():
            calls.append(1)
            return True

        self.assertTrue(ti.fillByLinkMap({(-1, 0): "vacuos", (0, 0): "potentia"}, onPlaced))
        self.assertEqual(len(calls), 2)
        self.assertEqual(sorted(ti.placed), [(-1, 0), (0, 0)])

    def test_fill_by_link_map_aborts_when_placed_callback_stops_it(self):
        # Проверка чернильницы после каждого выложенного аспекта: False прерывает выкладывание
        ti = makeInteractor()
        ti.makeAspects()
        calls = []

        def onPlaced():
            calls.append(1)
            return len(calls) < 2

        self.assertFalse(ti.fillByLinkMap(
            {(-1, 0): "vacuos", (0, 0): "potentia", (1, 0): "praecantatio"}, onPlaced))
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(ti.placed), 2)  # после False кликов больше нет

    def test_update_available_aspects_finishes_once(self):
        from types import SimpleNamespace
        ti = makeInteractor()
        ti.makeAspects()
        ti.rectAspectsListingLT = SimpleNamespace(x=0, y=0)
        ti.rectAspectsListingRB = SimpleNamespace(x=40, y=90)
        ti.rectAspectsListingLT2 = SimpleNamespace(x=100, y=0)
        ti.rectAspectsListingRB2 = SimpleNamespace(x=140, y=90)
        ti.availableAspects = []
        ti.moveMouseInSafePos = lambda: None
        ti.UI = SimpleNamespace(repaint=lambda: None, removeObject=lambda obj: None)
        ti.takeScreenshot = lambda *args, **kwargs: None
        ti._addDebugHighlightingRect = lambda *args, **kwargs: None

        class FakeNeurolink:
            @staticmethod
            def predict_inventory_aspects(image):
                return []

        originalNeurolink = interactorModule.Neurolink
        interactorModule.Neurolink = FakeNeurolink
        calls = []
        try:
            ti.updateAvailableAspectsInInventory(lambda: calls.append(1))
        finally:
            interactorModule.Neurolink = originalNeurolink
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
