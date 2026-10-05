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
