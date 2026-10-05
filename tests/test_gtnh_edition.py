import importlib
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
import gtnh.controls as gtnh_controls
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
        self.controlsPath = os.path.join(self.tmpdir.name, "gtnh_controls.json")
        self._origControlsPath = gtnh_controls.GTNH_THAUM_CONTROLS_CONFIG_PATH
        gtnh_controls.GTNH_THAUM_CONTROLS_CONFIG_PATH = self.controlsPath

    def tearDown(self):
        appstate_module.THAUM_VERSION_CONFIG_PATH = self._origVersionPath
        gtnh_controls.GTNH_THAUM_CONTROLS_CONFIG_PATH = self._origControlsPath
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

    def test_get_gtnh_versions(self):
        from gtnh import getGtnhVersions
        self.assertEqual(getGtnhVersions(), ["GTNH"])

    def test_appstate_merges_gtnh_recipes(self):
        editions.selectEdition("gtnh")
        AppState.rereadThaumVersion()
        self.assertEqual(AppState.selectedThaumVersion, "GTNH")
        self.assertIn("evolutio", AppState.aspectRecipes)
        self.assertIn("evolutio", AppState.allAddonsRecipes["Twist Space Technology"])

    def test_foreign_version_is_reset_when_selecting_gtnh(self):
        with open(self.versionPath, "w", encoding="utf-8") as file:
            json.dump({"version": "4.2.2.0 - 4.2.3.5"}, file)
        editions.selectEdition("gtnh")
        AppState.rereadThaumVersion()
        self.assertIsNone(AppState.selectedThaumVersion)
        self.assertEqual(AppState.aspectRecipes, {})

    def test_gtnh_version_is_accepted(self):
        editions.selectEdition("gtnh")
        AppState.rereadThaumVersion()
        self.assertEqual(AppState.selectedThaumVersion, "GTNH")
        self.assertIn("evolutio", AppState.aspectRecipes)

    def test_window_controls_delegation(self):
        edition = editions.selectEdition("gtnh")
        point = lambda x, y: SimpleNamespace(x=x, y=y)
        edition.saveThaumWindowControls(
            point(1, 2), point(3, 4),
            point(5, 6), point(7, 8),
            point(9, 10), point(11, 12),
            point(13, 14), point(15, 16), point(17, 18),
            19.0,
        )
        self.assertEqual(AppState.thaumWindowControls["rectAspectsListingLT2"], {"x": 9, "y": 10})
        self.assertEqual(AppState.thaumWindowControls["hexagonSlotSizeY"], 19.0)


if __name__ == "__main__":
    unittest.main()
