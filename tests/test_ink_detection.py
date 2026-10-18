import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.constants import INK_EXHAUSTED_MARKER_CELLS
from logic.InkDetection import isInkExhaustedByField, markerCellsBecameNone

MARKER_CELLS = {(0, 0), (1, 0)}


class IsInkExhaustedByFieldTest(unittest.TestCase):
    def test_disabled_when_marker_cells_are_empty(self):
        self.assertFalse(isInkExhaustedByField({(0, 0), (1, 0)}, markerCells=set()))
        self.assertFalse(isInkExhaustedByField(set(), markerCells=set()))

    def test_tracking_is_disabled_by_default(self):
        # Пока маркерные клетки не откалиброваны по скриншоту игры, фича выключена
        self.assertEqual(INK_EXHAUSTED_MARKER_CELLS, set())
        self.assertFalse(isInkExhaustedByField({(0, 0)}))

    def test_one_marker_cell_is_enough(self):
        self.assertTrue(isInkExhaustedByField({(0, 0)}, MARKER_CELLS))
        self.assertTrue(isInkExhaustedByField({(1, 0)}, MARKER_CELLS))
        self.assertTrue(isInkExhaustedByField({(0, 0), (1, 0)}, MARKER_CELLS))

    def test_other_none_cells_do_not_mean_exhaustion(self):
        self.assertFalse(isInkExhaustedByField({(-3, 2), (2, -1)}, MARKER_CELLS))

    def test_empty_field_means_no_exhaustion(self):
        self.assertFalse(isInkExhaustedByField(set(), MARKER_CELLS))


class MarkerCellsBecameNoneTest(unittest.TestCase):
    def test_marker_cell_became_none(self):
        # Клетка была свободной (или с аспектом) и вдруг перестала определяться
        self.assertTrue(markerCellsBecameNone(MARKER_CELLS, {(0, 0)}, {(0, 0)}))
        self.assertTrue(markerCellsBecameNone(MARKER_CELLS, {(0, 0), (1, 0), (-1, 0)}, {(-1, 0), (1, 0)}))

    def test_cell_was_not_known_before(self):
        # Клетка и раньше не определялась: это не признак исчерпания чернил
        self.assertFalse(markerCellsBecameNone(MARKER_CELLS, {(-2, 0)}, {(0, 0)}))

    def test_cell_is_still_known(self):
        self.assertFalse(markerCellsBecameNone(MARKER_CELLS, {(0, 0), (1, 0)}, set()))
        self.assertFalse(markerCellsBecameNone(MARKER_CELLS, {(0, 0)}, {(-1, 0)}))

    def test_disabled_when_marker_cells_are_empty(self):
        self.assertFalse(markerCellsBecameNone(set(), {(0, 0)}, {(0, 0)}))

    def test_empty_snapshot_means_no_exhaustion(self):
        self.assertFalse(markerCellsBecameNone(MARKER_CELLS, set(), {(0, 0)}))


if __name__ == "__main__":
    unittest.main()