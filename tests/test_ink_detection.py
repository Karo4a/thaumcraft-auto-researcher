import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.constants import (INK_EXHAUSTED_MARKER_CELLS, INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT,
                               INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE)
from logic.InkDetection import (collectFieldMarkers, isInkExhausted, markersLostSince, undetectedHexagons)

MARKER_CELLS = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0)}


class UndetectedHexagonsTest(unittest.TestCase):
    def test_aspect_cells_are_not_undetected(self):
        # noneHexagons из определения поля содержит и клетки с аспектами - это норма, не пропажа
        self.assertEqual(undetectedHexagons({(0, 0), (1, 0), (-1, 0)}, {(0, 0)}), {(1, 0), (-1, 0)})

    def test_nothing_undetected(self):
        self.assertEqual(undetectedHexagons({(0, 0)}, {(0, 0)}), set())
        self.assertEqual(undetectedHexagons(set(), set()), set())


class CollectFieldMarkersTest(unittest.TestCase):
    def test_present_and_lost_are_computed_for_marker_cells_only(self):
        # поле: (0,0) не опознана, (1,0) аспект, (-1,0) свободна, остальное вне полосы
        noneHexagons = {(0, 0), (1, 0), (2, 2)}
        freeHexagons = {(-1, 0)}
        markers = collectFieldMarkers({(1, 0)}, freeHexagons, noneHexagons, MARKER_CELLS)
        self.assertEqual(markers.present, {(-1, 0), (0, 0), (1, 0)})
        self.assertEqual(markers.lost, {(0, 0)})
        self.assertEqual(markers.visibleAspects, {(1, 0)})
        self.assertEqual(markers.observable, {(-1, 0), (0, 0)})
        self.assertAlmostEqual(markers.lostShare, 1 / 2)

    def test_no_marker_cells_on_field(self):
        markers = collectFieldMarkers(set(), set(), {(3, 3)}, MARKER_CELLS)
        self.assertEqual(markers.present, set())
        self.assertEqual(markers.lost, set())
        self.assertEqual(markers.lostShare, 0.0)

    def test_empty_marker_cells_disable_tracking(self):
        markers = collectFieldMarkers(set(), set(), {(0, 0), (1, 0)}, set())
        self.assertEqual(markers.present, set())
        self.assertFalse(isInkExhausted(markers))


class IsInkExhaustedTest(unittest.TestCase):
    def test_exhaustion_when_the_whole_band_is_lost(self):
        markers = collectFieldMarkers(set(), set(), MARKER_CELLS, MARKER_CELLS)
        self.assertTrue(isInkExhausted(markers))

    def test_no_exhaustion_when_the_band_is_detected(self):
        markers = collectFieldMarkers(set(), MARKER_CELLS, set(), MARKER_CELLS)
        self.assertFalse(isInkExhausted(markers))

    def test_sporadic_detection_misses_are_not_exhaustion(self):
        # В нормальном поле определение теряет 1-3 клетки: это не исчерпание чернил
        lost = {(-2, 0), (0, 0), (2, 0)}
        markers = collectFieldMarkers(set(), MARKER_CELLS - lost, lost, MARKER_CELLS)
        self.assertEqual(len(markers.lost), 3)
        self.assertFalse(isInkExhausted(markers))

    def test_share_alone_is_not_enough_for_a_too_small_band(self):
        # Крошечная полоса: доля максимальная, но клеток слишком мало
        markers = collectFieldMarkers(set(), set(), {(0, 0), (1, 0)}, {(0, 0), (1, 0)})
        self.assertEqual(markers.lostShare, 1.0)
        self.assertFalse(isInkExhausted(markers))

    def test_smallest_field_band_triggers(self):
        # Поле радиуса 2: маркерных клеток 7, при исчерпании пропадают все
        smallestBand = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1)}
        markers = collectFieldMarkers(set(), set(), smallestBand, smallestBand)
        self.assertEqual(len(markers.lost), 7)
        self.assertTrue(isInkExhausted(markers))


class MarkersLostSinceTest(unittest.TestCase):
    def test_only_cells_known_before_placing_count(self):
        # (0,0) была на месте до выкладывания и пропала, (1,0) и раньше не определялась
        markers = collectFieldMarkers(set(), set(), {(0, 0), (1, 0)}, MARKER_CELLS)
        lostSince = markersLostSince({(0, 0)}, markers)
        self.assertEqual(lostSince.lost, {(0, 0)})
        self.assertEqual(lostSince.present, markers.present)

    def test_nothing_lost_since_placing(self):
        markers = collectFieldMarkers(set(), MARKER_CELLS, set(), MARKER_CELLS)
        self.assertEqual(markersLostSince(MARKER_CELLS, markers).lost, set())


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
            markers = collectFieldMarkers(set(aspects), freeHexagons, noneHexagons)
            self.assertTrue(isInkExhausted(markers), f"{name}: исчерпание не распознано, {markers!r}")

    def test_real_exhaustion_logs_lose_almost_the_whole_band(self):
        # Числа из живых логов: 11 из 11 (радиус 3) и 12 из 13 (радиус 4, одна клетка занята superbia)
        radius3Markers = collectFieldMarkers(set(INK_LOG_SAMPLES["radius3"][0]),
                                            INK_LOG_SAMPLES["radius3"][1], INK_LOG_SAMPLES["radius3"][2])
        self.assertEqual((len(radius3Markers.lost), len(radius3Markers.observable)), (11, 11))
        radius4Markers = collectFieldMarkers(set(INK_LOG_SAMPLES["radius4"][0]),
                                            INK_LOG_SAMPLES["radius4"][1], INK_LOG_SAMPLES["radius4"][2])
        self.assertEqual((len(radius4Markers.lost), len(radius4Markers.present)), (12, 13))
        self.assertEqual(radius4Markers.visibleAspects, {(1, 0)})
        self.assertEqual((len(radius4Markers.lost), len(radius4Markers.observable)), (12, 12))

    def test_aspects_visible_under_the_plaque_do_not_dilute_the_share(self):
        # Аспекты под плашкой остаются распознанными: они не мешают понять,
        # что все остальные клетки полосы пропали
        aspects = {(0, 0): "superbia", (1, 0): "gelum", (2, 0): "aer"}
        noneHexagons = INK_EXHAUSTED_MARKER_CELLS | set(aspects)
        markers = collectFieldMarkers(aspects, set(), noneHexagons)
        self.assertEqual((len(markers.lost), len(markers.observable)), (10, 10))
        self.assertTrue(isInkExhausted(markers))

    def test_no_false_positive_when_marker_cells_are_free(self):
        # Если маркерные клетки на месте (чернила есть), срабатывания быть не должно
        for name, (aspects, freeHexagons, noneHexagons) in INK_LOG_SAMPLES.items():
            freeHexagons = freeHexagons | INK_EXHAUSTED_MARKER_CELLS
            noneHexagons = noneHexagons - INK_EXHAUSTED_MARKER_CELLS
            markers = collectFieldMarkers(set(aspects), freeHexagons, noneHexagons)
            self.assertFalse(isInkExhausted(markers), f"{name}: ложное срабатывание, {markers!r}")

    def test_aspects_and_free_marker_cells_are_not_exhaustion(self):
        # Часть маркерных клеток занята распознанными аспектами, остальные свободны:
        # ни одна не считается пропавшей
        aspects = {(0, 0): "aer", (1, 0): "ignis"}
        noneHexagons = set(aspects)  # свободные шестиугольники в noneHexagons не попадают
        markers = collectFieldMarkers(set(aspects), INK_EXHAUSTED_MARKER_CELLS - set(aspects), noneHexagons)
        self.assertEqual(markers.lost, set())
        self.assertFalse(isInkExhausted(markers))

    def test_lost_band_cells_holding_unknown_aspects_are_below_the_threshold(self):
        # Ложное срабатывание из живого прогона: сеть не опознала часть клеток полосы
        # (в том числе аспекты, которых бот не знает), но пропала не вся полоса
        lost = {(-4, 0), (-2, 0), (0, 0), (2, 0)}
        markers = collectFieldMarkers(set(), INK_EXHAUSTED_MARKER_CELLS - lost, lost)
        self.assertEqual((len(markers.lost), len(markers.present)), (4, 13))
        self.assertFalse(isInkExhausted(markers))


class CalibrationTest(unittest.TestCase):
    def test_marker_cells_are_the_centre_band_of_the_field(self):
        # Полоса в середине поля, которую закрывает плашка "You have run out of ink!"
        self.assertEqual(INK_EXHAUSTED_MARKER_CELLS, {
            (-4, 0), (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
            (-3, 1), (-1, 1), (1, 1), (3, 1),
        })

    def test_thresholds_are_below_the_real_exhaustion_numbers(self):
        # При исчерпании теряется 92-100% полосы, порог должен быть ниже с запасом
        self.assertLess(INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE, 0.92)
        self.assertLessEqual(INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT, 3)
        smallestFieldBand = {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1)}
        self.assertGreater(INK_EXHAUSTED_MARKER_CELLS_MIN_SHARE * len(smallestFieldBand),
                           INK_EXHAUSTED_MARKER_CELLS_MIN_COUNT)


if __name__ == "__main__":
    unittest.main()