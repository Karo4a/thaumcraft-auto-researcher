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
        ti.takeAspect(aspects["vacuos"])
        self.assertEqual(ti.taken, [])
        self.assertEqual(aspects["vacuos"].count, 0)

    def test_update_available_aspects_finishes_once(self):
        from types import SimpleNamespace
        ti = makeInteractor()
        ti.makeAspects()
        ti.rectAspectsListingLT = SimpleNamespace(x=0, y=0)
        ti.rectAspectsListingRB = SimpleNamespace(x=40, y=90)
        ti.rectAspectsListingLT2 = SimpleNamespace(x=100, y=0)
        ti.rectAspectsListingRB2 = SimpleNamespace(x=140, y=90)
        ti.availableAspects = []
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
