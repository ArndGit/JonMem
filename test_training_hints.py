import unittest

import training


class TestDirectionalHints(unittest.TestCase):
    def test_set_hint_writes_correct_field_and_strips(self):
        card = {"hint_de_to_en": "old_de", "hint_en_to_de": "old_en"}

        training.set_directional_hint(card, "de_to_en", "  neu_de  ")
        self.assertEqual(card["hint_de_to_en"], "neu_de")
        self.assertEqual(card["hint_en_to_de"], "old_en")

        training.set_directional_hint(card, "en_to_de", "\nneu_en\t")
        self.assertEqual(card["hint_en_to_de"], "neu_en")

    def test_get_hint_reads_correct_field(self):
        card = {"hint_de_to_en": "  a  ", "hint_en_to_de": "b"}
        self.assertEqual(training.get_directional_hint(card, "de_to_en"), "a")
        self.assertEqual(training.get_directional_hint(card, "en_to_de"), "b")


if __name__ == "__main__":
    unittest.main()
