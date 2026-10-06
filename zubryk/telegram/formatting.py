import logging

from telebot import apihelper, types

log = logging.getLogger("zubryk.formatting")
_rich_available = True


def send_rich(bot, chat_id, rich_html, fallback_html, keyboard=None):
    global _rich_available
    if _rich_available and hasattr(bot,"send_rich_message") and hasattr(types,"InputRichMessage"):
        try:
            return bot.send_rich_message(chat_id, types.InputRichMessage(html=rich_html, skip_entity_detection=True), reply_markup=keyboard)
        except apihelper.ApiTelegramException as exc:
            if exc.error_code not in (400, 404):
                raise
            log.warning("Rich Message unavailable; using readable HTML (API status %s)", exc.error_code)
            if exc.error_code == 404:
                _rich_available = False
    return bot.send_message(chat_id, fallback_html, parse_mode="HTML", reply_markup=keyboard)
