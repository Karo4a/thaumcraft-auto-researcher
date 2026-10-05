import importlib
import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

import editions
import configs.constants as base_constants
import gtnh.constants as gtnh_constants
from editions.vanilla import VanillaEdition
from gtnh import GtnhEdition

# NOTE: `from utils import utils` would give the `utils` package itself
# (utils/__init__.py rebinds the name `utils` to the package), so import the
# submodule explicitly.
utils = importlib.import_module("utils.utils")


class EditionConstantsValuesTest(unittest.TestCase):
    def test_base_delays(self):
        self.assertEqual(base_constants.DELAY_BETWEEN_EVENTS, 0.15)
        self.assertEqual(base_constants.DELAY_BETWEEN_RENDER, 0.5)
        self.assertEqual(VanillaEdition.delayBetweenEvents, 0.15)
        self.assertEqual(VanillaEdition.delayBetweenRender, 0.5)

    def test_gtnh_delays(self):
        self.assertEqual(gtnh_constants.DELAY_BETWEEN_EVENTS, 0.05)
        self.assertEqual(gtnh_constants.DELAY_BETWEEN_RENDER, 0.2)
        self.assertEqual(GtnhEdition.delayBetweenEvents, 0.05)
        self.assertEqual(GtnhEdition.delayBetweenRender, 0.2)

    def test_gtnh_overrides_base_delays(self):
        self.assertNotEqual(VanillaEdition.delayBetweenEvents, GtnhEdition.delayBetweenEvents)
        self.assertNotEqual(VanillaEdition.delayBetweenRender, GtnhEdition.delayBetweenRender)


class EditionConstantsUsageTest(unittest.TestCase):
    def tearDown(self):
        editions._currentEdition = None

    def _recordedSleeps(self):
        with mock.patch.object(utils, "time") as timeMock:
            utils.eventsDelay()
            utils.renderDelay()
        return timeMock.sleep.call_args_list

    def test_gtnh_delays_are_used_by_common_code(self):
        editions.selectEdition("gtnh")
        self.assertEqual(self._recordedSleeps(), [mock.call(0.05), mock.call(0.2)])

    def test_vanilla_delays_are_used_by_common_code(self):
        editions.selectEdition("vanilla")
        self.assertEqual(self._recordedSleeps(), [mock.call(0.15), mock.call(0.5)])

    def test_default_edition_is_vanilla(self):
        editions._currentEdition = None
        self.assertEqual(self._recordedSleeps(), [mock.call(0.15), mock.call(0.5)])


if __name__ == "__main__":
    unittest.main()
