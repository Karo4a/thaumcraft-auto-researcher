import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from configs.translations import TEXTS, TRANSLATIONS


def collectTextKeys() -> list[str]:
    keys = []
    for name, value in vars(TEXTS).items():
        if name.startswith("_") or name == "Buttons":
            continue
        if isinstance(value, str):
            keys.append(value)
    for name, value in vars(TEXTS.Buttons).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            keys.append(value)
    return keys


class TranslationsTest(unittest.TestCase):
    def test_all_languages_have_all_texts(self):
        keys = collectTextKeys()
        for language, texts in TRANSLATIONS.items():
            missing = [key for key in keys if key not in texts]
            self.assertEqual([], missing, f"{language} misses keys: {missing}")

    def test_new_edition_texts_are_translated(self):
        for language, texts in TRANSLATIONS.items():
            for key in (TEXTS.chooseEdition, TEXTS.openAllAspects, TEXTS.chooseGtnhVersion):
                self.assertTrue(texts[key], f"{language} has empty {key}")
                self.assertNotEqual(texts[key], key, f"{language} did not translate {key}")


if __name__ == "__main__":
    unittest.main()
