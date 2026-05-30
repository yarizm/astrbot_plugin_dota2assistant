import unittest

from core.opendota import _is_radiant_win, _extract_item_description


class TestHelpers(unittest.TestCase):
    def test_is_radiant_win_radiant_player_wins(self):
        data = {"radiant_win": True, "player_slot": 1}
        self.assertTrue(_is_radiant_win(data))

    def test_is_radiant_win_radiant_player_loses(self):
        data = {"radiant_win": False, "player_slot": 1}
        self.assertFalse(_is_radiant_win(data))

    def test_is_radiant_win_dire_player_wins(self):
        data = {"radiant_win": False, "player_slot": 128}
        self.assertTrue(_is_radiant_win(data))

    def test_is_radiant_win_dire_player_loses(self):
        data = {"radiant_win": True, "player_slot": 128}
        self.assertFalse(_is_radiant_win(data))

    def test_extract_item_description_with_abilities(self):
        item = {
            "abilities": [{"description": "Active: Blink"}, {"description": "Cooldown: 15s"}],
            "hint": ["Some hint"],
        }
        result = _extract_item_description(item)
        self.assertIn("Blink", result)
        self.assertIn("Cooldown", result)
        self.assertIn("hint", result)

    def test_extract_item_description_empty(self):
        result = _extract_item_description({})
        self.assertEqual(result, "")

    def test_extract_item_description_truncation(self):
        item = {"abilities": [{"description": "x" * 500}], "hint": []}
        result = _extract_item_description(item)
        self.assertLessEqual(len(result), 300)


if __name__ == "__main__":
    unittest.main()
