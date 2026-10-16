import unittest
from datetime import datetime, timedelta
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from telebot import apihelper
from zubryk.config import TIMEZONE
from zubryk.catalog import WORD_GROUPS
from zubryk.telegram import cards, formatting, keyboards

# Import decorators with an offline token; no test can contact the real bot.
with patch("zubryk.config.BOT_TOKEN", "123456:offline"):
    from zubryk.telegram import handlers, presentation, scheduler


def api_error(code, description):
    return apihelper.ApiTelegramException("test", None, {"error_code": code, "description": description})


def message(text=None):
    return SimpleNamespace(
        message_id=99, chat=SimpleNamespace(id=7, type="private"),
        from_user=SimpleNamespace(id=7, first_name="Друг"), text=text,
    )


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class FormattingTests(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.addCleanup(patch.stopall)
        patch.object(formatting, "_rich_available", True).start()

    def test_navigation_edits_instead_of_sending(self):
        formatting.send_html(self.bot, 7, "<b>Меню</b>", message=message())
        self.bot.edit_message_text.assert_called_once()
        self.bot.send_message.assert_not_called()
        self.assertTrue(self.bot.edit_message_text.call_args.kwargs["link_preview_options"].is_disabled)

    def test_repeated_click_does_not_duplicate_screen(self):
        original = message()
        self.bot.edit_message_text.side_effect = api_error(400, "Bad Request: message is not modified")
        self.assertIs(formatting.send_html(self.bot, 7, "Меню", message=original), original)
        self.bot.send_message.assert_not_called()

    def test_deleted_message_gets_a_new_screen(self):
        self.bot.edit_message_text.side_effect = api_error(400, "Bad Request: message to edit not found")
        formatting.send_html(self.bot, 7, "Меню", message=message())
        self.bot.send_message.assert_called_once()

    def test_rate_limit_and_invalid_html_are_not_retried_as_new_messages(self):
        for code, description in ((429, "Too Many Requests"), (403, "Forbidden"), (400, "can't parse entities")):
            with self.subTest(code=code):
                self.bot.edit_message_text.side_effect = api_error(code, description)
                with self.assertRaises(apihelper.ApiTelegramException):
                    formatting.send_html(self.bot, 7, "Меню", message=message())
        self.bot.send_message.assert_not_called()

    def test_rich_navigation_uses_rich_parameter_without_text(self):
        formatting.send_rich(self.bot, 7, "<h2>Меню</h2>", "<b>Меню</b>", message=message())
        kwargs = self.bot.edit_message_text.call_args.kwargs
        self.assertEqual(kwargs["rich_message"].html, "<h2>Меню</h2>")
        self.assertNotIn("text", kwargs)
        self.bot.send_rich_message.assert_not_called()

    def test_unavailable_rich_messages_keep_html_and_keyboard(self):
        kb = keyboards.home_only_kb()
        self.bot.send_rich_message.side_effect = api_error(404, "Not Found")
        formatting.send_rich(self.bot, 7, "<h2>Меню</h2>", "<b>Меню</b>", kb)
        self.assertFalse(formatting._rich_available)
        self.bot.send_message.assert_called_once()
        self.assertIs(self.bot.send_message.call_args.kwargs["reply_markup"], kb)
        self.assertEqual(self.bot.send_message.call_args.args[1], "<b>Меню</b>")

    def test_rich_edit_falls_back_to_html_in_same_message(self):
        self.bot.edit_message_text.side_effect = [api_error(400, "Rich messages are unavailable"), message()]
        formatting.send_rich(self.bot, 7, "<h2>Меню</h2>", "<b>Меню</b>", message=message())
        self.assertEqual(self.bot.edit_message_text.call_count, 2)
        self.bot.send_message.assert_not_called()


class CardTests(unittest.TestCase):
    def test_word_translation_is_hidden_and_dynamic_html_is_escaped(self):
        html = cards.study_word_text("<слова>", "А & Б", "<тэма>")
        self.assertIn("<tg-spoiler>А &amp; Б</tg-spoiler>", html)
        self.assertNotIn("<слова>", html)
        self.assertNotIn("<тэма>", html)

    def test_word_source_and_license_remain_visible(self):
        with patch.object(cards, "word_source", return_value={"url": "https://example.test/?a=1&b=2", "licenseUrl": "https://example.test/license"}):
            html = cards.study_word_text("слова", "слово", "Тэма")
        self.assertIn("Викисловарь", html)
        self.assertIn("CC BY-SA 4.0", html)
        self.assertIn("?a=1&amp;b=2", html)

    def test_daily_digest_hides_each_translation_and_keeps_attribution(self):
        with patch.object(cards, "word_source", return_value={"url": "https://example.test/word", "licenseUrl": "https://example.test/license"}):
            rich, html = cards.daily_words_card([(1, "слова", "слово"), (2, "дом", "дом")])
        for content in (rich, html):
            self.assertEqual(content.count("<tg-spoiler>"), 2)
            self.assertIn("CC BY-SA 4.0", content)

    def test_stale_streak_is_not_shown_as_active(self):
        today = datetime.now(TIMEZONE).date()
        user = {"streak": 12, "last_activity_date": today - timedelta(days=2)}
        self.assertEqual(cards.current_streak(user), 0)
        user["last_activity_date"] = today - timedelta(days=1)
        self.assertEqual(cards.current_streak(user), 12)

    def test_all_catalog_cards_fit_telegram_text_limit(self):
        for group in WORD_GROUPS.values():
            for bel, ru in group["words"]:
                parser = PlainText()
                parser.feed(cards.study_word_text(bel, ru, group["name"]))
                # Telegram counts UTF-16 code units after entity parsing.
                length = len("".join(parser.parts).encode("utf-16-le")) // 2
                self.assertLessEqual(length, 4096)

    def test_user_name_cannot_inject_markup(self):
        user = {"name": "<b>Имя</b>", "balance": 1200, "daily_time": None}
        for html in (cards.main_menu_text(user), cards.main_menu_rich(user), cards.settings_text(user, "Не присылать")):
            self.assertIn("&lt;b&gt;Имя&lt;/b&gt;", html)


class KeyboardTests(unittest.TestCase):
    def test_all_topic_callback_payloads_fit_telegram_limit(self):
        groups = [{"key": key, "name": data["name"]} for key, data in WORD_GROUPS.items()]
        with patch.object(keyboards.db, "get_groups", return_value=groups):
            for prefix in ("sg", "pg"):
                for page in range((len(groups) + 7) // 8):
                    kb = keyboards.groups_kb(prefix, page).to_dict()
                    for row in kb["inline_keyboard"]:
                        for button in row:
                            self.assertLessEqual(len(button["callback_data"].encode()), 64)

    def test_current_time_is_selected_and_off_is_on_its_own_row(self):
        rows = keyboards.daily_time_kb(True, selected="1200").to_dict()["inline_keyboard"]
        selected = [button for row in rows for button in row if button.get("style") == "success"]
        self.assertEqual([button["callback_data"] for button in selected], ["settime:1200"])
        self.assertEqual(len(rows[-2]), 1)
        self.assertEqual(rows[-2][0]["callback_data"], "settime:off")

    def test_share_and_copy_use_exact_game_link(self):
        link = "https://t.me/example_bot?start=g_example"
        kb = keyboards.invitation_kb(link).to_dict()["inline_keyboard"]
        self.assertEqual(parse_qs(urlparse(kb[0][0]["url"]).query)["url"], [link])
        self.assertEqual(kb[1][0]["copy_text"]["text"], link)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.bot = MagicMock()
        self.bot.send_message.return_value = message()
        self.bot.edit_message_text.return_value = message()
        self.addCleanup(patch.stopall)
        for module in (handlers, presentation, scheduler):
            patch.object(module, "bot", self.bot).start()

    def test_page_counter_does_not_cancel_pending_test(self):
        call = SimpleNamespace(id="cb", message=message())
        with patch.object(handlers.db, "get_or_create_user") as get_user:
            handlers._dispatch_callback(call, 7, 7, "noop")
        self.bot.clear_step_handler_by_chat_id.assert_not_called()
        get_user.assert_not_called()

    def test_menu_cancels_pending_answer_and_updates_current_screen(self):
        call = SimpleNamespace(id="cb", message=message())
        with patch.object(handlers.db, "get_or_create_user", return_value={"name": "Друг", "balance": 0}), patch.object(keyboards, "get_mini_app_url", return_value=""):
            handlers._dispatch_callback(call, 7, 7, "menu")
        self.bot.clear_step_handler_by_chat_id.assert_called_once_with(7)
        self.bot.edit_message_text.assert_called_once()
        self.bot.send_message.assert_not_called()

    def test_two_question_session_preserves_scoring_and_reports_result(self):
        with patch.object(handlers.db, "start_test", return_value=2), patch.object(handlers.db, "get_next_test_word", side_effect=[(1, "дом", "дом"), (2, "лес", "лес"), None]), patch.object(handlers.db, "record_test_answer") as record, patch.object(handlers.db, "pop_test_word") as pop:
            handlers.start_test_flow(7, 7)
            first = self.bot.register_next_step_handler.call_args.args[2:]
            handlers.check_test_answer(message("Дом"), *first)
            second = self.bot.register_next_step_handler.call_args.args[2:]
            handlers.check_test_answer(message("неверно"), *second)
        self.assertEqual(record.call_count, 2)
        self.assertEqual(record.call_args_list[0].args, (7, 1, True))
        self.assertEqual(record.call_args_list[1].args, (7, 2, False))
        self.assertEqual(pop.call_count, 2)
        html = self.bot.send_message.call_args.args[1]
        self.assertIn("1 из 2", html)
        self.assertIn("Тест завершён", html)
        # One bot reply per answer includes feedback and the next question/result.
        self.assertEqual(self.bot.send_message.call_count, 3)

    def test_non_text_answer_is_not_recorded_as_wrong(self):
        with patch.object(handlers.db, "record_test_answer") as record, patch.object(handlers.db, "pop_test_word") as pop:
            handlers.check_test_answer(message(), 1, "дом", 2, 0, 0)
        record.assert_not_called()
        pop.assert_not_called()
        self.bot.register_next_step_handler.assert_called_once()

    def test_command_is_not_recorded_as_wrong_answer(self):
        with patch.object(handlers, "cmd_help") as help_handler, patch.object(handlers.db, "record_test_answer") as record:
            msg = message("/help")
            handlers.check_test_answer(msg, 1, "дом", 2, 0, 0)
        help_handler.assert_called_once_with(msg)
        record.assert_not_called()

    def test_daily_delivery_failure_does_not_advance_learning(self):
        with patch.object(scheduler.db, "get_users_due_for_daily", return_value=[7]), patch.object(scheduler.db, "get_next_new_words_multi", return_value=[(1, "дом", "дом")]), patch.object(scheduler, "send_rich", side_effect=RuntimeError("offline")), patch.object(scheduler.db, "mark_word_learned") as learn, patch.object(scheduler.db, "mark_daily_sent") as sent, self.assertLogs("zubryk.scheduler", level="ERROR"):
            scheduler.send_daily_words_for_time("1200")
        learn.assert_not_called()
        sent.assert_not_called()

    def test_failed_word_delivery_does_not_mark_word_learned(self):
        with patch.object(handlers.db, "get_group", return_value={"name": "Тэма"}), patch.object(handlers.db, "get_next_new_word", return_value=(1, "дом", "дом")), patch.object(handlers.db, "mark_word_learned") as learn, patch.object(handlers, "send_screen", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                handlers.show_study_word(7, 7, "home")
        learn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
