import json
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

with open(os.path.join(ROOT, "src", "gtnh", "data", "aspects_configs", "gtnhAspectsRecipes.json"),
          encoding="utf-8") as file:
    GTNH_RECIPES = json.load(file)["GTNH"]


def makeAspects(recipes=RECIPES, counts=None):
    counts = counts or {}
    aspects = {}
    for name, recipe in recipes.items():
        default = 5 if len(recipe) == 0 else 0
        aspects[name] = FakeAspect(name, counts.get(name, default))
    return aspects


def plan(aspects, targetName, targetCount, recipes=RECIPES):
    return planMixing(aspects[targetName], targetCount,
                      lambda aspectName: aspects[aspectName],
                      lambda aspectName: recipes[aspectName])


def planByName(planOfMixing):
    return {aspect.name: times for aspect, times in planOfMixing}


def planNames(planOfMixing):
    return [aspect.name for aspect, _ in planOfMixing]


def executePlan(planOfMixing, aspects, recipes=RECIPES):
    """Исполняет план как GtnhThaumInteractor.mixAspect: 1 микс съедает по 1 копии каждого ингредиента."""
    for aspectRecipe, mixingTimes in planOfMixing:
        for ingredientName in recipes[aspectRecipe.name]:
            ingredient = aspects[ingredientName]
            if (ingredient.count or 0) < mixingTimes:
                raise AssertionError(f"{aspectRecipe.name} x{mixingTimes} needs {ingredientName}, "
                                     f"but only {ingredient.count} left")
            ingredient.count -= mixingTimes
        aspects[aspectRecipe.name].count += mixingTimes


class MixingPlanTest(unittest.TestCase):
    def _makeAspects(self, counts=None):
        return makeAspects(RECIPES, counts)

    def _plan(self, aspects, name, targetCount):
        return plan(aspects, name, targetCount, RECIPES)

    def test_builds_chain_bottom_up(self):
        aspects = self._makeAspects()
        planOfMixing = self._plan(aspects, "praecantatio", 1)
        self.assertEqual(planNames(planOfMixing), ["potentia", "vacuos", "praecantatio"])
        executePlan(planOfMixing, aspects)
        self.assertEqual(aspects["praecantatio"].count, 1)

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
        aspects = makeAspects(recipes)
        planOfMixing = plan(aspects, "root", 1, recipes)
        times = planByName(planOfMixing)
        self.assertEqual((times["z"], times["l1"], times["l2"]), (2, 1, 1))
        executePlan(planOfMixing, aspects, recipes)
        self.assertEqual(aspects["root"].count, 1)

    def test_returns_none_when_shared_basic_ingredient_is_insufficient(self):
        # Общий базовый ингредиент нужен двум миксам: одной копии aer на них не хватит
        recipes = dict(RECIPES)
        recipes["l1"] = ["aer", "ignis"]
        recipes["l2"] = ["aer", "terra"]
        recipes["root"] = ["l1", "l2"]
        aspects = makeAspects(recipes, counts={"aer": 1})
        self.assertIsNone(plan(aspects, "root", 1, recipes))

    def test_plan_uses_existing_ingredients_without_deep_recursion(self):
        # Прямых ингредиентов хватает: миксуется только сам аспект, вглубь не идём
        recipes = dict(RECIPES)
        recipes["a"] = ["c", "d"]
        recipes["root"] = ["a", "b"]
        recipes["b"] = []
        recipes["c"] = []
        recipes["d"] = []
        aspects = makeAspects(recipes)
        aspects["a"].count = 5
        aspects["b"].count = 5
        aspects["c"].count = 0
        self.assertEqual(planByName(plan(aspects, "root", 1, recipes)), {"root": 1})

    def test_none_count_is_initialized_to_zero(self):
        aspects = self._makeAspects()
        aspects["vacuos"].count = None
        planOfMixing = self._plan(aspects, "vacuos", 1)
        self.assertIsNotNone(planOfMixing)
        self.assertEqual(aspects["vacuos"].count, 0)

    def test_plan_mixes_missing_ingredient_instead_of_failing(self):
        # Регресс на лог: fabrico требовал bestia x2, а motus в стоке был один
        aspects = makeAspects(GTNH_RECIPES, counts={"motus": 1, "victus": 2})
        planOfMixing = plan(aspects, "fabrico", 1, GTNH_RECIPES)
        self.assertIsNotNone(planOfMixing)
        times = planByName(planOfMixing)
        self.assertEqual(times["bestia"], 2)
        self.assertEqual(times["motus"], 1)
        executePlan(planOfMixing, aspects, GTNH_RECIPES)
        self.assertEqual(aspects["fabrico"].count, 1)

    def test_plan_mixes_ingredient_that_is_only_craftable(self):
        # victus в стоке нет вовсе: план обязан смешать его из базовых до микса bestia
        counts = {name: 10 for name, recipe in GTNH_RECIPES.items() if not recipe}
        counts.update({"motus": 1, "victus": 0})
        aspects = makeAspects(GTNH_RECIPES, counts=counts)
        planOfMixing = plan(aspects, "fabrico", 1, GTNH_RECIPES)
        self.assertIsNotNone(planOfMixing)
        names = planNames(planOfMixing)
        self.assertIn("victus", names)
        self.assertLess(names.index("victus"), names.index("bestia"))
        executePlan(planOfMixing, aspects, GTNH_RECIPES)
        self.assertEqual(aspects["fabrico"].count, 1)

    def test_every_gtnh_plan_is_executable(self):
        for basicsCount in (10, 40):
            for name in GTNH_RECIPES:
                aspects = makeAspects(GTNH_RECIPES, counts={
                    aspectName: (basicsCount if not recipe else 0)
                    for aspectName, recipe in GTNH_RECIPES.items()
                })
                planOfMixing = plan(aspects, name, 1, GTNH_RECIPES)
                if planOfMixing is None:
                    continue
                with self.subTest(aspect=name, basics=basicsCount):
                    executePlan(planOfMixing, aspects, GTNH_RECIPES)
                    self.assertEqual(aspects[name].count, 1)


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
