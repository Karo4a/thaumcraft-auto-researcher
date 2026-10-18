import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.constants import INK_EXHAUSTED_MARKER_CELLS, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT
from logic.InkDetection import (isInkExhaustedByField, markerCellsBecameUndetected, undetectedHexagons)

MARKER_CELLS = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0)}


class UndetectedHexagonsTest(unittest.TestCase):
    def test_aspect_cells_are_not_undetected(self):
        # noneHexagons из определения поля содержит и клетки с аспектами - это норма, не пропажа
        self.assertEqual(undetectedHexagons({(0, 0), (1, 0), (-1, 0)}, {(0, 0)}), {(1, 0), (-1, 0)})

    def test_nothing_undetected(self):
        self.assertEqual(undetectedHexagons({(0, 0)}, {(0, 0)}), set())
        self.assertEqual(undetectedHexagons(set(), set()), set())


class IsInkExhaustedByFieldTest(unittest.TestCase):
    def test_exhaustion_when_marker_cells_are_undetected(self):
        self.assertTrue(isInkExhaustedByField(MARKER_CELLS, MARKER_CELLS, 1))
        self.assertTrue(isInkExhaustedByField(MARKER_CELLS, MARKER_CELLS, len(MARKER_CELLS)))

    def test_no_exhaustion_when_marker_cells_are_detected(self):
        self.assertFalse(isInkExhaustedByField(set(), MARKER_CELLS, 1))
        self.assertFalse(isInkExhaustedByField({(-2, 2), (2, -2)}, MARKER_CELLS, 1))

    def test_threshold_tolerates_detection_misses(self):
        markers = sorted(MARKER_CELLS)
        self.assertLessEqual(INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT, len(markers))
        self.assertFalse(isInkExhaustedByField(set(markers[:INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT - 1])))
        self.assertTrue(isInkExhaustedByField(set(markers[:INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT])))

    def test_disabled_when_marker_cells_are_empty(self):
        self.assertFalse(isInkExhaustedByField(MARKER_CELLS, set(), 1))

    def test_min_count_zero_means_always_exhausted(self):
        # Страховка от неверной конфигурации: нулевой порог считается вручную
        self.assertFalse(isInkExhaustedByField({(-3, 2), (2, -1)}, MARKER_CELLS, 1))
        self.assertTrue(isInkExhaustedByField({(-3, 2), (2, -1)}, {(-3, 2)}, 1))


class MarkerCellsBecameUndetectedTest(unittest.TestCase):
    def test_marker_cell_became_undetected(self):
        # Клетка была свободной (или с аспектом) и вдруг перестала определяться
        self.assertTrue(markerCellsBecameUndetected(MARKER_CELLS, MARKER_CELLS, MARKER_CELLS, 1))
        self.assertTrue(markerCellsBecameUndetected(MARKER_CELLS, MARKER_CELLS, {(0, 0)}, 1))

    def test_cell_was_not_known_before(self):
        # Клетка и раньше не определялась: это не признак исчерпания чернил
        self.assertFalse(markerCellsBecameUndetected(MARKER_CELLS, {(-2, 0)}, {(0, 0)}, 1))

    def test_cell_is_still_known(self):
        self.assertFalse(markerCellsBecameUndetected(MARKER_CELLS, MARKER_CELLS, set(), 1))
        self.assertFalse(markerCellsBecameUndetected(MARKER_CELLS, {(0, 0)}, {(-1, 0)}, 1))

    def test_disabled_when_marker_cells_are_empty(self):
        self.assertFalse(markerCellsBecameUndetected(set(), MARKER_CELLS, MARKER_CELLS))

    def test_empty_snapshot_means_no_exhaustion(self):
        self.assertFalse(markerCellsBecameUndetected(MARKER_CELLS, set(), MARKER_CELLS, 1))


# Реальные определения поля из логов игры в момент исчерпания чернильницы:
# (existingAspects, freeHexagons, noneHexagons) - как их отдаёт getExistingAspectsOnField.
# noneHexagons включает клетки с аспектами, как в оригинальном коде.
INK_LOG_SAMPLES = {
    "radius3": (
        {(0, -2): "permutatio", (-2, 1): "instrumentum"},
        {(0, 1), (2, -1), (1, 2), (-1, -1), (-2, -1), (1, -1), (0, 2), (-1, 2), (0, -1)},
        {(3, -1), (3, 1), (-3, 0), (2, 2), (1, 0), (1, 3), (-2, -2), (-1, -2), (-2, 1), (-1, 1),
         (3, 0), (-3, 2), (0, -2), (2, -2), (2, 1), (-2, 0), (-1, 0), (3, 2), (-2, 2), (-3, -1),
         (0, -3), (-3, 1), (0, 0), (1, 1), (0, 3), (2, 0), (1, -2)},
    ),
    "radius4": (
        {(-4, 2): "auram", (-4, -2): "praecantatio", (4, -2): "alienis", (0, -4): "cognitio",
         (0, 4): "vacuos", (1, 0): "superbia", (4, 2): "lucrum"},
        {(3, -2), (3, -1), (-3, 3), (0, 2), (1, -3), (2, 2), (1, 3), (-4, -1), (-4, 1), (-2, -1),
         (-1, -2), (-2, -2), (-1, -1), (-2, 1), (-1, 4), (3, 3), (-3, 2), (0, -1), (0, -2),
         (0, 1), (2, -1), (2, -2), (1, 2), (2, 1), (-1, 3), (-2, 3), (4, -1), (3, 2), (-1, 2),
         (4, 1), (-3, -1), (0, -3), (-3, -2), (2, -3), (0, 3), (1, -1), (1, -2), (1, 4), (-2, 2)},
        {(4, 0), (3, 1), (-3, 0), (0, -4), (1, 0), (-4, -2), (-1, 1), (4, 2), (3, 0), (0, 4),
         (-4, 0), (-2, -3), (-1, -3), (-2, 0), (-1, 0), (4, -2), (-3, 1), (0, 0), (1, 1), (2, 0),
         (2, 3), (-4, 2)},
    ),
}


class RealLogSamplesTest(unittest.TestCase):
    def test_real_exhaustion_logs_are_detected(self):
        for name, (aspects, freeHexagons, noneHexagons) in INK_LOG_SAMPLES.items():
            undetected = undetectedHexagons(noneHexagons, set(aspects))
            self.assertTrue(isInkExhaustedByField(undetected), f"{name}: исчерпание не распознано")

    def test_no_false_positive_when_marker_cells_are_free(self):
        # Если маркерные клетки на месте (чернила есть), срабатывания быть не должно
        for name, (aspects, freeHexagons, noneHexagons) in INK_LOG_SAMPLES.items():
            freeHexagons = freeHexagons | INK_EXHAUSTED_MARKER_CELLS
            noneHexagons = noneHexagons - INK_EXHAUSTED_MARKER_CELLS
            undetected = undetectedHexagons(noneHexagons, set(aspects))
            self.assertFalse(isInkExhaustedByField(undetected), f"{name}: ложное срабатывание")

    def test_aspects_and_free_marker_cells_are_not_exhaustion(self):
        # Часть маркерных клеток занята распознанными аспектами, остальные свободны:
        # ни одна не считается пропавшей
        aspects = {(0, 0): "aer", (1, 0): "ignis"}
        noneHexagons = set(aspects)  # свободные шестиугольники в noneHexagons не попадают
        undetected = undetectedHexagons(noneHexagons, set(aspects))
        self.assertEqual(undetected, set())
        self.assertFalse(isInkExhaustedByField(undetected))


class CalibrationTest(unittest.TestCase):
    def test_marker_cells_are_the_centre_band_of_the_field(self):
        # Полоса в середине поля, которую закрывает плашка "You have run out of ink!"
        self.assertEqual(INK_EXHAUSTED_MARKER_CELLS, {
            (-4, 0), (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
            (-3, 1), (-1, 1), (1, 1), (3, 1),
        })

    def test_min_count_fits_the_smallest_field(self):
        # В самом маленьком поле (радиус 2) маркерных клеток 7, порог должен быть ниже
        smallestFieldBand = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1)}
        self.assertLess(INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT, len(smallestFieldBand))


if __name__ == "__main__":
    unittest.main()