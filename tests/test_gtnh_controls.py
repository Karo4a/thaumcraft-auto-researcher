import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from gtnh.controls import readGtnhThaumWindowControls, saveGtnhThaumWindowControls


class GtnhControlsTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "gtnh_controls.json")
            point = lambda x, y: SimpleNamespace(x=x, y=y)
            saveGtnhThaumWindowControls(
                point(1, 2), point(3, 4),
                point(5, 6), point(7, 8),
                point(9, 10), point(11, 12),
                point(13, 14), point(15, 16), point(17, 18),
                19.0, path=path,
            )
            loaded = readGtnhThaumWindowControls(path=path)
            self.assertEqual(loaded["pointWritingMaterials"], {"x": 1, "y": 2})
            self.assertEqual(loaded["rectAspectsListingLT2"], {"x": 9, "y": 10})
            self.assertEqual(loaded["rectAspectsListingRB2"], {"x": 11, "y": 12})
            self.assertEqual(loaded["hexagonSlotSizeY"], 19.0)

    def test_missing_file_returns_none(self):
        self.assertIsNone(readGtnhThaumWindowControls(path="/no/such/file.json"))


if __name__ == "__main__":
    unittest.main()
