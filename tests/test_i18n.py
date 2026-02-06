import json
import tempfile
from pathlib import Path

import pytest

from blunder_tutor.i18n.manager import TranslationManager, format_message


class TestFormatMessage:
    def test_simple_string(self):
        assert format_message("Hello world") == "Hello world"

    def test_placeholder_substitution(self):
        assert format_message("Hello {name}", {"name": "Alice"}) == "Hello Alice"

    def test_multiple_placeholders(self):
        result = format_message("{a} and {b}", {"a": "X", "b": "Y"})
        assert result == "X and Y"

    def test_missing_placeholder_kept(self):
        assert format_message("Hello {name}") == "Hello {name}"

    def test_english_plural_one(self):
        msg = "{count, plural, one {# item} other {# items}}"
        assert format_message(msg, {"count": 1}, "en") == "1 item"

    def test_english_plural_other(self):
        msg = "{count, plural, one {# item} other {# items}}"
        assert format_message(msg, {"count": 5}, "en") == "5 items"

    def test_english_plural_zero(self):
        msg = "{count, plural, one {# item} other {# items}}"
        assert format_message(msg, {"count": 0}, "en") == "0 items"

    def test_russian_plural_one(self):
        msg = "{count, plural, one {# задача} few {# задачи} many {# задач} other {# задач}}"
        assert format_message(msg, {"count": 1}, "ru") == "1 задача"

    def test_russian_plural_few(self):
        msg = "{count, plural, one {# задача} few {# задачи} many {# задач} other {# задач}}"
        assert format_message(msg, {"count": 3}, "ru") == "3 задачи"

    def test_russian_plural_many(self):
        msg = "{count, plural, one {# задача} few {# задачи} many {# задач} other {# задач}}"
        assert format_message(msg, {"count": 5}, "ru") == "5 задач"

    def test_russian_plural_11(self):
        msg = "{count, plural, one {# задача} few {# задачи} many {# задач} other {# задач}}"
        assert format_message(msg, {"count": 11}, "ru") == "11 задач"

    def test_russian_plural_21(self):
        msg = "{count, plural, one {# задача} few {# задачи} many {# задач} other {# задач}}"
        assert format_message(msg, {"count": 21}, "ru") == "21 задача"

    def test_exact_match(self):
        msg = "{count, plural, =0 {no items} one {# item} other {# items}}"
        assert format_message(msg, {"count": 0}, "en") == "no items"

    def test_plural_with_surrounding_text(self):
        msg = "You have {count, plural, one {# puzzle} other {# puzzles}} to solve"
        assert format_message(msg, {"count": 3}, "en") == "You have 3 puzzles to solve"

    def test_unknown_locale_falls_back_to_english(self):
        msg = "{count, plural, one {# item} other {# items}}"
        assert format_message(msg, {"count": 1}, "xx") == "1 item"


class TestTranslationManager:
    @pytest.fixture
    def locales_dir(self, tmp_path):
        en = {
            "greeting": "Hello",
            "farewell": "Goodbye {name}",
            "items": "{count, plural, one {# item} other {# items}}",
        }
        ru = {
            "greeting": "Привет",
            "items": "{count, plural, one {# предмет} few {# предмета} many {# предметов} other {# предметов}}",
        }
        (tmp_path / "en.json").write_text(json.dumps(en), encoding="utf-8")
        (tmp_path / "ru.json").write_text(json.dumps(ru), encoding="utf-8")
        return tmp_path

    def test_available_locales(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.available_locales() == ["en", "ru"]

    def test_translate_english(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("en", "greeting") == "Hello"

    def test_translate_russian(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("ru", "greeting") == "Привет"

    def test_fallback_to_english(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("ru", "farewell", name="World") == "Goodbye World"

    def test_missing_key_returns_key(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("en", "nonexistent.key") == "nonexistent.key"

    def test_plural_english(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("en", "items", count=1) == "1 item"
        assert mgr.t("en", "items", count=5) == "5 items"

    def test_plural_russian(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        assert mgr.t("ru", "items", count=1) == "1 предмет"
        assert mgr.t("ru", "items", count=3) == "3 предмета"
        assert mgr.t("ru", "items", count=5) == "5 предметов"

    def test_get_all_english(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        all_en = mgr.get_all("en")
        assert all_en["greeting"] == "Hello"
        assert "farewell" in all_en

    def test_get_all_russian_merges_with_english(self, locales_dir):
        mgr = TranslationManager(locales_dir)
        all_ru = mgr.get_all("ru")
        assert all_ru["greeting"] == "Привет"
        assert all_ru["farewell"] == "Goodbye {name}"

    def test_empty_locales_dir(self, tmp_path):
        mgr = TranslationManager(tmp_path)
        assert mgr.available_locales() == []
        assert mgr.t("en", "anything") == "anything"

    def test_nonexistent_dir(self, tmp_path):
        mgr = TranslationManager(tmp_path / "nonexistent")
        assert mgr.available_locales() == []


class TestRealLocales:
    @pytest.fixture
    def mgr(self):
        locales_dir = Path(__file__).parent.parent / "locales"
        return TranslationManager(locales_dir)

    def test_russian_available(self, mgr):
        assert "ru" in mgr.available_locales()

    def test_russian_plural_heatmap(self, mgr):
        assert mgr.t("ru", "heatmap.total", count=1) == "1 задача"
        assert mgr.t("ru", "heatmap.total", count=3) == "3 задачи"
        assert mgr.t("ru", "heatmap.total", count=5) == "5 задач"
        assert mgr.t("ru", "heatmap.total", count=21) == "21 задача"

    def test_russian_fallback_for_missing_key(self, mgr):
        # settings.locale.label exists in both, but if we add a new en key not in ru
        # it should fall back
        en_keys = set(mgr.get_all("en").keys())
        ru_keys = set(mgr.get_all("ru").keys())
        # All ru keys should be a subset of en keys (since get_all merges)
        assert en_keys == ru_keys

    def test_russian_trainer_feedback(self, mgr):
        result = mgr.t("ru", "trainer.feedback.found_best", move="Nf3")
        assert "Nf3" in result
        assert "нашли" in result.lower()


class TestEnJsonIntegrity:
    def test_en_json_loads_and_has_trainer_keys(self):
        en_path = Path(__file__).parent.parent / "locales" / "en.json"
        with open(en_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "trainer.title" in data
        assert "trainer.feedback.excellent" in data
        assert "common.loading" in data
        assert "nav.trainer" in data
        assert "chess.phase.opening" in data
        assert "heatmap.total" in data

    def test_en_json_all_values_are_strings(self):
        en_path = Path(__file__).parent.parent / "locales" / "en.json"
        with open(en_path, encoding="utf-8") as f:
            data = json.load(f)

        for key, value in data.items():
            assert isinstance(value, str), (
                f"Key {key} has non-string value: {type(value)}"
            )

    def test_en_json_no_html_in_values(self):
        en_path = Path(__file__).parent.parent / "locales" / "en.json"
        with open(en_path, encoding="utf-8") as f:
            data = json.load(f)

        for key, value in data.items():
            assert "<" not in value or ">" not in value, (
                f"Key {key} contains HTML: {value}"
            )
