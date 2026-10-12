import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from controllers.ThaumInteractor import ThaumInteractor


class FakeAspect:
    nextUid = 0

    def __init__(self, name, count=0):
        self.name = name
        self.uid = FakeAspect.nextUid
        FakeAspect.nextUid += 1
        self.count = count
        self.cellX = 0
        self.cellY = 0


def makeInteractor(aspectNames):
    ti = ThaumInteractor.__new__(ThaumInteractor)
    ti.allAspects = [FakeAspect(name, 1) for name in aspectNames]
    ti.currentAspectsPageIdx = 0
    ti.taken = []
    ti.placed = []
    ti.scrollToLeftSide = lambda: None
    ti.takeAspect = lambda aspect: ti.taken.append(aspect.name)
    ti.putAspect = lambda cellX, cellY: ti.placed.append((cellX, cellY))
    return ti


class VanillaFillByLinkMapTest(unittest.TestCase):
    def test_returns_true_and_places_all_aspects(self):
        ti = makeInteractor(["vacuos", "potentia"])
        self.assertTrue(ti.fillByLinkMap({(-1, 0): "vacuos", (0, 0): "potentia"}))
        self.assertEqual(sorted(ti.taken), ["potentia", "vacuos"])
        self.assertEqual(sorted(ti.placed), [(-1, 0), (0, 0)])
        self.assertIsNone(ti.currentAspectsPageIdx)

    def test_returns_true_for_empty_link_map(self):
        ti = makeInteractor(["vacuos"])
        self.assertTrue(ti.fillByLinkMap({}))
        self.assertEqual(ti.taken, [])
        self.assertEqual(ti.placed, [])


if __name__ == "__main__":
    unittest.main()