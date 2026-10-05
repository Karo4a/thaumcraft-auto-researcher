import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.mixing import planMixing, selectCraftableAspects


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

    def test_returns_plan_with_times(self):
        aspects = self._makeAspects()
        plan = self._plan(aspects, "vacuos", 3)
        planByName = {aspect.name: times for aspect, times in plan}
        self.assertEqual(planByName, {"vacuos": 3})

    def test_shared_intermediate_accumulates_needed_times(self):
        recipes = dict(RECIPES)
        recipes["z"] = ["aer", "ignis"]
        recipes["l1"] = ["z", "aqua"]
        recipes["l2"] = ["z", "terra"]
        recipes["root"] = ["l1", "l2"]
        aspects = {}
        for name, recipe in recipes.items():
            aspects[name] = FakeAspect(name, 5 if len(recipe) == 0 else 0)
        plan = planMixing(
            aspects["root"], 1,
            lambda aspectName: aspects[aspectName],
            lambda aspectName: recipes[aspectName],
        )
        self.assertIsNotNone(plan)
        planByName = {aspect.name: times for aspect, times in plan}
        self.assertEqual(planByName["z"], 2)
        self.assertEqual(planByName["l1"], 1)
        self.assertEqual(planByName["l2"], 1)

    def test_shared_ingredient_shortfall_is_documented_quirk(self):
        # Наследие master: план может вернуться, хотя базового аспекта не хватит на все миксы.
        # Исполняющий код (GtnhThaumInteractor.mixAspect) обязан сам проверять counts.
        recipes = dict(RECIPES)
        recipes["l1"] = ["aer", "ignis"]
        recipes["l2"] = ["aer", "terra"]
        recipes["root"] = ["l1", "l2"]
        aspects = {}
        for name, recipe in recipes.items():
            aspects[name] = FakeAspect(name, 5 if len(recipe) == 0 else 0)
        aspects["aer"] = FakeAspect("aer", 1)
        plan = planMixing(
            aspects["root"], 1,
            lambda aspectName: aspects[aspectName],
            lambda aspectName: recipes[aspectName],
        )
        self.assertIsNotNone(plan)

    def test_none_when_deeper_ingredient_empty_even_if_direct_ingredients_sufficient(self):
        # Наследие master: рецепт раскрывается глубже, даже если прямые ингредиенты уже есть.
        # b/c/d объявлены базовыми, иначе getAspectRecipeByName упал бы с KeyError.
        recipes = dict(RECIPES)
        recipes["a"] = ["c", "d"]
        recipes["root"] = ["a", "b"]
        recipes["b"] = []
        recipes["c"] = []
        recipes["d"] = []
        aspects = {}
        for name, recipe in recipes.items():
            aspects[name] = FakeAspect(name, 5 if len(recipe) == 0 else 0)
        aspects["a"] = FakeAspect("a", 5)
        aspects["b"] = FakeAspect("b", 5)
        aspects["c"] = FakeAspect("c", 0)
        plan = planMixing(
            aspects["root"], 1,
            lambda aspectName: aspects[aspectName],
            lambda aspectName: recipes[aspectName],
        )
        self.assertIsNone(plan)

    def test_none_count_is_initialized_to_zero(self):
        aspects = self._makeAspects()
        aspects["vacuos"].count = None
        plan = self._plan(aspects, "vacuos", 1)
        self.assertIsNotNone(plan)
        self.assertEqual(aspects["vacuos"].count, 0)


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


if __name__ == "__main__":
    unittest.main()
