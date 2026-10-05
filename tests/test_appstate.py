import importlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
from editions.base import BaseEdition
from utils import AppState

appstate_module = importlib.import_module("utils.AppState")


class FakeEdition(BaseEdition):
    def extraAspectRecipes(self):
        return {"Test Edition": {"aer": [], "testaspect": ["aer", "ignis"]}}

    def extraAddonsRecipes(self):
        return {"Test Addon": {"testaddon": ["aer", "aqua"]}}


class AppStateEditionTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.versionPath = os.path.join(self.tmpdir.name, "version.json")
        with open(self.versionPath, "w", encoding="utf-8") as file:
            json.dump({"version": "Test Edition"}, file)
        self._origVersionPath = appstate_module.THAUM_VERSION_CONFIG_PATH
        appstate_module.THAUM_VERSION_CONFIG_PATH = self.versionPath

    def tearDown(self):
        appstate_module.THAUM_VERSION_CONFIG_PATH = self._origVersionPath
        editions._currentEdition = None
        self.tmpdir.cleanup()

    def test_edition_recipes_are_merged_and_selected(self):
        editions._currentEdition = FakeEdition()
        AppState.rereadThaumVersion()
        self.assertIn("Test Edition", AppState.allAspectRecipes)
        self.assertEqual(AppState.selectedThaumVersion, "Test Edition")
        self.assertIn("testaspect", AppState.aspectRecipes)
        self.assertIn("testaddon", AppState.aspectRecipes)

    def test_unknown_version_is_reset(self):
        # версия "Test Edition" есть только у FakeEdition, поэтому для vanilla она неизвестна
        AppState.rereadThaumVersion()
        self.assertIsNone(AppState.selectedThaumVersion)
        self.assertEqual(AppState.aspectRecipes, {})

    def test_edition_selection_roundtrip(self):
        path = os.path.join(self.tmpdir.name, "edition.json")
        self._origEditionPath = appstate_module.EDITION_CONFIG_PATH
        appstate_module.EDITION_CONFIG_PATH = path
        try:
            AppState.saveEdition("gtnh")
            self.assertEqual(AppState.selectedEdition, "gtnh")
            AppState.selectedEdition = None
            AppState.rereadAllConfigs()
            self.assertEqual(AppState.selectedEdition, "gtnh")
        finally:
            appstate_module.EDITION_CONFIG_PATH = self._origEditionPath

    def test_edition_valid_versions_guard(self):
        with open(self.versionPath, "w", encoding="utf-8") as file:
            json.dump({"version": "Some Version"}, file)

        class StrictEdition(FakeEdition):
            def validVersionKeys(self):
                return {"Some Version"}

            def extraAspectRecipes(self):
                return {"Some Version": {"aer": []}}

        editions._currentEdition = StrictEdition()
        AppState.rereadThaumVersion()
        self.assertEqual(AppState.selectedThaumVersion, "Some Version")

    def test_unknown_edition_is_reset(self):
        path = os.path.join(self.tmpdir.name, "unknown_edition.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"edition": "no_such_edition"}, file)
        self._origEditionPath = appstate_module.EDITION_CONFIG_PATH
        appstate_module.EDITION_CONFIG_PATH = path
        try:
            AppState.rereadEdition()
            self.assertIsNone(AppState.selectedEdition)
        finally:
            appstate_module.EDITION_CONFIG_PATH = self._origEditionPath


if __name__ == "__main__":
    unittest.main()
