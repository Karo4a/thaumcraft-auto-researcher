import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.recognition import aspects_count, filterByMaxConfidence, splitAspectsAndDigits


class Pred:
    def __init__(self, name, x, y, confidence=0.9, width=32, height=32):
        self.predictionName = name
        self.x = x
        self.y = y
        self.confidence = confidence
        self.width = width
        self.height = height


class RecognitionTest(unittest.TestCase):
    def test_split(self):
        preds = [Pred("ignis", 0, 0), Pred("4", 1, 1), Pred("aqua", 2, 2)]
        aspects, digits = splitAspectsAndDigits(preds)
        self.assertEqual([p.predictionName for p in aspects], ["ignis", "aqua"])
        self.assertEqual([p.predictionName for p in digits], ["4"])

    def test_filter_by_max_confidence(self):
        preds = [Pred("ignis", 0, 0, 0.5), Pred("ignis", 1, 1, 0.9), Pred("aqua", 2, 2, 0.3)]
        filtered = filterByMaxConfidence(preds)
        self.assertEqual(len(filtered), 2)
        ignis = next(p for p in filtered if p.predictionName == "ignis")
        self.assertEqual(ignis.confidence, 0.9)

    def test_aspects_count(self):
        aspect = Pred("ignis", 10, 10)
        digits = [Pred("1", 8, 10), Pred("2", 12, 10)]
        self.assertEqual(aspects_count([aspect], digits), {"ignis": 12})

    def test_aspects_count_ignores_digits_outside_aspect(self):
        aspect = Pred("ignis", 100, 100)
        digits = [Pred("7", 10, 10)]
        self.assertEqual(aspects_count([aspect], digits), {"ignis": 0})

    def test_remove_same_spot_predictions_keeps_higher_confidence(self):
        from gtnh.recognition import remove_same_spot_predictions
        preds = [Pred("1", 10.0, 0, 0.5), Pred("2", 10.5, 0, 0.9)]
        result = remove_same_spot_predictions(preds)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].predictionName, "2")

    def test_remove_same_spot_predictions_anchor_quirk_is_documented(self):
        # Anchor-based merge (parity): 1.9 и 3.7 не сливаются, хотя разница < 2.0
        from gtnh.recognition import remove_same_spot_predictions
        preds = [Pred("1", 0.0, 0, 0.10), Pred("2", 1.9, 0, 0.99), Pred("3", 3.7, 0, 0.90)]
        result = remove_same_spot_predictions(preds)
        self.assertEqual([p.predictionName for p in result], ["2", "3"])

    def test_is_aspect(self):
        from gtnh.recognition import is_aspect
        self.assertFalse(is_aspect(Pred("4", 0, 0)))
        self.assertTrue(is_aspect(Pred("ignis", 0, 0)))

    def test_aspects_count_duplicate_aspect_last_wins(self):
        from gtnh.recognition import aspects_count
        first = Pred("ignis", 10, 10)   # бокс покрывает цифру "1"
        second = Pred("ignis", 50, 10)  # бокс покрывает цифру "2"
        digits = [Pred("1", 10, 10), Pred("2", 50, 10)]
        self.assertEqual(aspects_count([first, second], digits), {"ignis": 2})

    def test_modules_import_without_heavy_dependencies(self):
        import subprocess
        script = (
            "import sys;"
            "sys.path.insert(0, 'src');"
            "import gtnh.recognition, gtnh.mixing;"
            "print(','.join(m for m in ('PyQt5', 'PyQt6', 'PIL', 'onnxruntime') if m in sys.modules))"
        )
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual("", result.stdout.strip(), result.stderr)


if __name__ == "__main__":
    unittest.main()
